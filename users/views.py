import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django import forms
from django.http import HttpResponse

from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from .models import SearchResultHistoryModel, HandleModel, ClaimModel, SaveItemModel, ClaimLikeModel
from .forms import CustomUserCreationForm, HomeForm, UploadForm, ClaimForm, SaveItemForm, ClaimLikeForm
from .token_generator import account_activation_token
from .esETD import elasticsearchfun

from django.contrib import messages
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.files.storage import FileSystemStorage
import bleach

#     form_class = CustomUserCreationForm
#     success_url = reverse_lazy('login')
#     template_name = 'signup.html'


def SignUpView(request):
    form = CustomUserCreationForm

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            email_subject = 'Activate Your Account'

            message = render_to_string('activateaccount.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(email_subject, message, to=[to_email])
            email.send()
            return redirect('accountconfirmation')
    else:
        form = CustomUserCreationForm()

    return render(request, 'signup.html', {'form': form})


def activateaccount(request, uidb64, token):

    try:
        uid = force_bytes(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):

        user.is_active = True
        user.save()
        login(request, user)
        form = HomeForm()

        context = {'uidb64': uidb64, 'token': token,
                   'form': [], 'text': "Your account is activated!"}
        return render(request, 'accountactivated.html', context)
    else:
        form = HomeForm()
        context = {'form': []}
        return render(request, 'home.html', context)


def accountconfirmation(request):
    template_name = 'accountconfirmation.html'
    return render(request, template_name)


def accountactivated(request):
    template_name = 'accountactivated.html'
    return render(request, template_name)


class HomePageView(TemplateView):
    template_name = 'home.html'

    print("entering home page")

    def get(self, request):
        form = HomeForm()
        args = {'form': form}
        return render(request, self.template_name, args)

    # taking the input from the search page
    def post(self, request):
        form = HomeForm(request.POST)
        if form.is_valid():
            whattosearch = filtersearchtext(form)
            # saving user history if the user is loggedin
            historysave(request, form, whattosearch)
            request.session["whattosearch"] = whattosearch
            return redirect('serp')

        else:
            msg = 0
            searchtext = ""
            output = ["Not valid input"]

        args = {'form': form, 'msg': msg, 'output': output, 'text': searchtext}
        return render(request, self.template_name, args)


def historysave(request, form, whattosearch):
    if request.user.is_authenticated:
        searchhistorystore = form.save(commit=False)
        searchhistorystore.user = request.user
        searchhistorystore.searchtext = whattosearch['title']
        searchhistorystore.save()


def SERPView(request):
    template_name = 'serp.html'

    if request.method == 'GET':
        form = HomeForm()
        whattosearch = request.session["whattosearch"]

        suggested_search = ""
        print("whattosearch.",  whattosearch["title"])
        for arg in whattosearch["title"].split():
            output, msg = elasticsearchfun(
                arg, type="spellcheck")
            print(arg, output)
            if len(output) > 1:
                suggested_search = suggested_search+output[1]+" "
            else:
                suggested_search = suggested_search+arg+" "
        suggested_search = suggested_search[:-1]
        print(suggested_search)
        if suggested_search == whattosearch["title"]:
            wrongspellflag = 0
        else:
            wrongspellflag = 1

        whattosearch["title"] = suggested_search

        output, msg = elasticsearchfun(whattosearch)

        searchtext = ''

        for key in whattosearch.keys():
            if key not in ['date1', 'date2']:
                searchtext = searchtext+whattosearch[key]+", "
        searchtext = searchtext+"between " + \
            whattosearch['date1']+" and "+whattosearch['date2']

        total_docs = len(output)
        output = paginationfun(output,  request,  10)

        args = {'form': form, 'msg': msg, 'output': output,
                'text': searchtext, 'total_docs': total_docs,
                "high_text_inp": whattosearch["title"],
                "wrongspellflag": wrongspellflag,
                "suggested_search": suggested_search}
        return render(request, template_name, args)

    if request.method == 'POST':
        form = HomeForm(request.POST)
        if form.is_valid():
            whattosearch = filtersearchtext(form)
            # saving user history if the user is loggedin
            historysave(request, form, whattosearch)
            request.session["whattosearch"] = whattosearch
            return redirect('serp')
        else:
            msg = 0
            searchtext = ""
            output = ["Not valid input"]

        form = HomeForm()
        args = {'form': form, 'msg': msg, 'output': output, 'text': searchtext}
        return render(request, template_name, args)

    args = {'form': form, 'msg': 0, 'output': [
        "Some issue with SERPview"], 'text': ''}
    return render(request, template_name, args)


def SERPdetailsView(request):
    template_name = 'serpdetails.html'

    if request.method == 'GET':
        form = ClaimForm()

        handle = request.session["handle"]
        whattosearch = {"handle": handle}
        output, msg = elasticsearchfun(whattosearch, type="handlequery")

        pdfmsg, pdfnames = pdflinks(output, 0, handle)

        allclaims_objects = ClaimModel.objects.filter(handle=handle)
        allclaims = []
        for arg in allclaims_objects:
            dum_dict = {}
            dum_dict["handle"] = arg.handle
            dum_dict["source_Code"] = arg.source_Code
            dum_dict["claim_field"] = arg.claim_field
            dum_dict["Can_you_reproduce_this_claim"] = arg.Can_you_reproduce_this_claim
            dum_dict["experiments_and_results"] = arg.experiments_and_results
            dum_dict["datasets"] = arg.datasets

            if request.user.id == arg.user_id:
                dum_dict["authorized_user"] = 1
            else:
                dum_dict["authorized_user"] = 0

            dum_dict["id"] = arg.id

            dum_dict["idliked"] = str(arg.id)+",Liked"
            dum_dict["idunliked"] = str(arg.id)+",Unliked"
            dum_dict["idnetliked"] = str(arg.id)+",Net"

            dum_dict["totallikes"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, star=1))
            dum_dict["totalunlikes"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, star=0))
            dum_dict["netlikes"] = dum_dict["totallikes"] - \
                dum_dict["totalunlikes"]

            dum_dict["liked"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, user_id=request.user.id, star=1))
            dum_dict["unliked"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, user_id=request.user.id, star=0))

            allclaims.append(dum_dict)

        try:
            pdfnames = output[0]["relation_haspart"]
            if str(type(pdfnames)) == "<class 'str'>":
                pdfnames = [pdfnames]

            fnames = []
            for fname in pdfnames:
                dumdict = {}
                dumdict['url'] = "http://127.0.0.1:8000/media/dissertation/" + \
                    handle+"/"+fname

                dumdict['name'] = fname
                fnames.append(dumdict)
        except:
            msg = 0
            fnames = []
            output = ["PDF files not found"]

        args = {'form': form, 'output': output, 'pdfmsg': pdfmsg, 'pdfnames': pdfnames,
                'msg': msg, 'fnames': fnames, 'handle': handle, 'allclaims': allclaims, 'allclaims_length': len(allclaims)}
        return render(request, template_name, args)

    if request.method == 'POST':
        form = ClaimForm()

        handle = request.POST.get('handle', None)
        whattosearch = {"handle": handle}
        output, msg = elasticsearchfun(whattosearch, type="handlequery")

        pdfmsg, pdfnames = pdflinks(output, 0, handle)

        allclaims_objects = ClaimModel.objects.filter(handle=handle)
        allclaims = []
        for arg in allclaims_objects:
            dum_dict = {}
            dum_dict["handle"] = arg.handle
            dum_dict["source_Code"] = arg.source_Code
            dum_dict["claim_field"] = arg.claim_field
            dum_dict["Can_you_reproduce_this_claim"] = arg.Can_you_reproduce_this_claim
            dum_dict["experiments_and_results"] = arg.experiments_and_results
            dum_dict["datasets"] = arg.datasets

            if request.user.id == arg.user_id:
                dum_dict["authorized_user"] = 1
            else:
                dum_dict["authorized_user"] = 0

            dum_dict["id"] = arg.id

            dum_dict["idliked"] = str(arg.id)+",Liked"
            dum_dict["idunliked"] = str(arg.id)+",Unliked"
            dum_dict["idnetliked"] = str(arg.id)+",Net"

            dum_dict["totallikes"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, star=1))
            dum_dict["totalunlikes"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, star=0))
            dum_dict["netlikes"] = dum_dict["totallikes"] - \
                dum_dict["totalunlikes"]

            dum_dict["liked"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, user_id=request.user.id, star=1))
            dum_dict["unliked"] = len(
                ClaimLikeModel.objects.filter(claim_id=arg.id, user_id=request.user.id, star=0))

            allclaims.append(dum_dict)

        try:
            pdfnames = output[0]["relation_haspart"]
            if str(type(pdfnames)) == "<class 'str'>":
                pdfnames = [pdfnames]

            fnames = []
            for fname in pdfnames:
                dumdict = {}
                dumdict['url'] = "http://127.0.0.1:8000/media/dissertation/" + \
                    handle+"/"+fname

                dumdict['name'] = fname
                fnames.append(dumdict)
        except:
            msg = 0
            fnames = []
            output = ["PDF files not found"]

        args = {'form': form, 'output': output, 'pdfmsg': pdfmsg, 'pdfnames': pdfnames,
                'msg': msg, 'fnames': fnames, 'handle': handle, 'allclaims': allclaims, 'allclaims_length': len(allclaims)}
        return render(request, template_name, args)

    return render(request, template_name)


def pdflinks(output, hnum, handle):

    try:
        pdfmsg = 1
        rawpdfnames = output[hnum]["relation_haspart"]
        if str(type(rawpdfnames)) == "<class 'str'>":
            rawpdfnames = [rawpdfnames]

        pdfnames = []
        for fname in rawpdfnames:
            dumdict = {}
            dumdict['url'] = "http://127.0.0.1:8000/media/dissertation/" + \
                handle+"/"+fname

            dumdict['name'] = fname
            pdfnames.append(dumdict)
    except:
        pdfmsg = 0
        pdfnames = []

    return pdfmsg, pdfnames


def paginationfun(output, request, numpages):
    page = request.GET.get('page', 1)
    # arg_1: list of objects & arg_2: num of objects per page
    paginator = Paginator(output, numpages)
    try:
        output = paginator.page(page)
    except PageNotAnInteger:
        output = paginator.page(1)
    except EmptyPage:
        output = paginator.page(paginator.num_pages)

    return output


def UploadView(request):

    msg = 0
    if request.method == 'GET':
        form = UploadForm()

    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():

            whattoindex = {}
            # indexing strings
            whattoindex['title'] = form.cleaned_data["title"]
            whattoindex['contributor_author'] = form.cleaned_data["contributor_author"]
            whattoindex['description_abstract'] = form.cleaned_data["description_abstract"]
            whattoindex['contributor_committeechair'] = form.cleaned_data["contributor_committeechair"]
            whattoindex['contributor_department'] = form.cleaned_data["contributor_department"]
            whattoindex['date_issued'] = str(form.cleaned_data["date_issued"])
            whattoindex['identifier_sourceurl'] = form.cleaned_data["identifier_sourceurl"]

            # Uploading comitte membsers into list
            comitmembs = form.cleaned_data["contributor_committeemember"]
            try:
                comitmembs = comitmembs.split('"')[1::2]
                if len(comitmembs) == 0:
                    comitmembs = form.cleaned_data["contributor_committeemember"]
                    comitmembs = comitmembs.split()[1::2]
                if len(comitmembs) == 0:
                    comitmembs = [
                        form.cleaned_data["contributor_committeemember"]]
            except:
                comitmembs = [form.cleaned_data["contributor_committeemember"]]
            whattoindex['contributor_committeemember'] = comitmembs

            # Uploading subject into list
            keywords = form.cleaned_data["contributor_committeemember"]
            try:
                keywords = keywords.split('"')[1::2]
                if len(keywords) == 0:
                    keywords = form.cleaned_data["subject"]
                    keywords = keywords.split()[1::2]
                if len(keywords) == 0:
                    keywords = [form.cleaned_data["subject"]]
            except:
                keywords = [form.cleaned_data["subject"]]
            whattoindex['subject'] = keywords

            # uplodaing thehandle number by querying the model database
            handleobjects = HandleModel.objects.all()
            if len(handleobjects) == 0:
                handlenum = 29581
            else:
                handlenum = int(handleobjects[len(handleobjects)-1].handle)+1
            # increasing the current handle number by 1 in the database
            if request.user.is_authenticated:
                handlestore = form.save(commit=False)
                handlestore.user = request.user
                handlestore.handle = str(handlenum)
                handlestore.save()
            whattoindex['handle'] = handlenum

            # Uploading the relation_haspart into list
            uploaded_file = request.FILES['file']
            fs = FileSystemStorage("media/dissertation/"+str(handlenum)+"/")
            fs.save(uploaded_file.name, uploaded_file)
            whattoindex['relation_haspart'] = [uploaded_file.name]
            output, msg = elasticsearchfun(whattoindex, type="index")

        else:
            form = UploadForm()

    args = {"form": form, "msg": msg}

    return render(request, 'upload.html', args)


def bleachcleanfun(form, arg):
    return bleach.clean(form.cleaned_data[arg], strip=True, tags=[''])


def filtersearchtext(form):

    searchtext = bleachcleanfun(form, 'searchtext')
    whattosearch = {'title': searchtext}

    contributor_department = bleachcleanfun(form, 'contributor_department')
    if contributor_department != '':
        whattosearch['contributor_department'] = contributor_department

    contributor_author = bleachcleanfun(form, 'contributor_author')
    if contributor_author != '':
        whattosearch['contributor_author'] = contributor_author

    contributor_committeechair = bleachcleanfun(
        form, 'contributor_committeechair')
    if contributor_committeechair != '':
        whattosearch['contributor_committeechair'] = contributor_committeechair

    description_degree = bleachcleanfun(form, 'description_degree')
    if description_degree != '':
        whattosearch['description_degree'] = description_degree

    whattosearch['date1'] = str(form.cleaned_data['date1'])
    whattosearch['date2'] = str(form.cleaned_data['date2'])

    return whattosearch


def DeleteItemView(request):
    if request.method == 'GET':
        return redirect('saveitem')
    if request.method == 'POST':
        deleteitemid = request.POST.get('deleteitemid', None)
        if int(deleteitemid) == -1:
            SaveItemModel.objects.filter(user_id=request.user.id).delete()
        else:
            SaveItemModel.objects.filter(id=deleteitemid).delete()
        return redirect('saveitem')


def ClaimSubmitView(request):

    msg = 0
    if request.method == 'GET':
        print("Entered get")
        form = ClaimForm()

    if request.method == 'POST':
        form = ClaimForm(request.POST)

        if form.is_valid():

            handle = request.POST.get('handle', None)

            if request.user.is_authenticated:
                claimstore = form.save(commit=False)
                claimstore.user = request.user
                claimstore.handle = str(handle)

                claimstore.source_Code = form.cleaned_data['source_Code']
                claimstore.claim_field = form.cleaned_data['claim_field']
                claimstore.Can_you_reproduce_this_claim = form.cleaned_data[
                    'Can_you_reproduce_this_claim']
                claimstore.datasets = form.cleaned_data['datasets']
                claimstore.experiments_and_results = form.cleaned_data['experiments_and_results']

                claimstore.save()

                request.session["handle"] = handle
                return redirect('serpdetails')

    return render(request, 'upload.html')


def delete_claim_view(request):

    if request.method == "POST":
        print("CLAIM")

        neel = request.POST.get('neel', None)
        print(neel, request.session["handle"])

        ClaimLikeModel.objects.filter(claim_id=int(neel)).delete()
        ClaimModel.objects.filter(id=int(neel)).delete()
        # request.session["handle"] = handle
        return redirect('/serpdetails')


def getuseritems(request):
    usersitems = SaveItemModel.objects.filter(user_id=request.user.id)
    output = []
    for arg in usersitems:
        whattosearch = {"handle": arg.handle}
        dumoutput, msg = elasticsearchfun(whattosearch, type="handlequery")
        dumoutput[0]["id"] = arg.id
        output.append(dumoutput[0])
    return output


def SaveItemView(request):

    template_name = 'saveitem.html'
    if request.method == 'GET':
        if request.user.is_authenticated:
            form = SaveItemForm()
            output = getuseritems(request)
            numresults = len(output)
            output = paginationfun(output, request, 5)

            args = {'form': form, 'msgtext': "",
                    'output': output, 'numresults': numresults}
            return render(request, template_name, args)
        else:
            return redirect('home')

    if request.method == 'POST':
        handle = request.POST.get('handle', None)

        try:
            form = SaveItemForm()
            saveitems = form.save(commit=False)
            saveitems.user = request.user
            saveitems.handle = handle
            saveitems.save()
            return redirect('saveitem')
        except:
            form = SaveItemForm()
            output = getuseritems(request)
            numresults = len(output)
            output = paginationfun(output, request, 5)

            args = {'form': form, 'msgtext': "Previously saved",
                    'output': output, 'numresults': numresults}
            return render(request, template_name, args)


def index(request):
    posts = ClaimLikeModel.objects.all()
    form = ClaimLikeForm
    context = {
        'form': form,
        'posts': posts
    }

    return render(request, 'index.html', context)


def ClaimLikeView(request):

    if request.method == 'GET':
        idcrude = request.GET.get('idcrude')

        print(idcrude)
        likeorunlike = idcrude.split(',')[1]

        claim_id = int(idcrude.split(',')[0])

        allclaims_objects = ClaimModel.objects.filter(id=claim_id)
        for arg in allclaims_objects:
            handle = arg.handle

        claimlike_objects = ClaimLikeModel.objects

        if len(claimlike_objects.filter(user_id=request.user.id, claim_id=claim_id)):
            for arg in claimlike_objects.filter(user_id=request.user.id, claim_id=claim_id):
                star = arg.star
            if (likeorunlike == "Liked" and star == 1) or (likeorunlike == "Unliked" and star == 0):
                claimlike_objects.filter(
                    user_id=request.user.id, claim_id=claim_id).delete()
            elif (likeorunlike == "Liked" and star == 0):
                p = claimlike_objects.get(
                    user_id=request.user.id, claim_id=claim_id)
                p.star = 1
                p.save()
            elif (likeorunlike == "Unliked" and star == 1):
                p = claimlike_objects.get(
                    user_id=request.user.id, claim_id=claim_id)
                p.star = 0
                p.save()
        else:
            form = ClaimLikeForm()
            likeitems = form.save(commit=False)
            likeitems.user = request.user
            likeitems.handle = handle
            likeitems.claim_id = claim_id
            if idcrude.split(',')[1] == "Liked":
                likeitems.star = 1
            else:
                likeitems.star = 0

            likeitems.save()

        result = {}
        result["liked"] = len(claimlike_objects.filter(
            user_id=request.user.id, claim_id=claim_id, star=1))

        result["unliked"] = len(claimlike_objects.filter(
            user_id=request.user.id, claim_id=claim_id, star=0))

        result["idliked"] = str(claim_id)+",Liked"
        result["idunliked"] = str(claim_id)+",Unliked"
        result["idnetliked"] = str(claim_id)+",Net"

        result["likecount"] = len(
            claimlike_objects.filter(claim_id=claim_id, star=1))
        result["unlikecount"] = len(
            claimlike_objects.filter(claim_id=claim_id, star=0))
        result["netcount"] = result["likecount"] - result["unlikecount"]

        return JsonResponse(result)


# ---------------------------------------------------------------

def AutoCompleteView(request):

    if request.method == 'GET':
        textsearch = request.GET.get('term', '')

        output, msg = elasticsearchfun(
            textsearch.split()[-1], type="spellcheck")
        for i in range(0, len(output)):
            dum = ""
            for arg in textsearch.split()[:-1]:
                dum = dum+" "+arg
            output[i] = dum+" "+output[i]

        data = json.dumps(output)
        mimetype = 'application/json'
        return HttpResponse(data, mimetype)

    if request.method == 'POST':
        pass
