from django.shortcuts import render, redirect
from django import forms

from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from .models import SearchResultHistoryModel, HandleModel,  ClaimModel
from .forms import CustomUserCreationForm, HomeForm, UploadForm, ClaimForm
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
                'text': searchtext, 'total_docs': total_docs}
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

        args = {'form': form, 'output': output,
                'msg': msg, 'fnames': fnames, 'handle': handle, 'allclaims': allclaims, 'allclaims_length': len(allclaims)}
        return render(request, template_name, args)

    if request.method == 'POST':

        form = ClaimForm()

        handle = request.POST.get('handle', None)
        whattosearch = {"handle": handle}
        output, msg = elasticsearchfun(whattosearch, type="handlequery")

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

        args = {'form': form, 'output': output,
                'msg': msg, 'fnames': fnames, 'handle': handle, 'allclaims': allclaims, 'allclaims_length': len(allclaims)}
        return render(request, template_name, args)

    return render(request, template_name)


def paginationfun(output, request, numpages):
    page = request.GET.get('page', 5)
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
