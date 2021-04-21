from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, SearchResultHistoryModel, HandleModel, ClaimModel, SaveItemModel, ClaimLikeModel
from django.forms import CheckboxInput, HiddenInput
import datetime


class CustomUserCreationForm(UserCreationForm):

    email = forms.EmailField(required=True)

    def clean_email(self):
        if CustomUser.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError(
                "the given email is already registered")
        return self.cleaned_data['email']

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('username',  'email', 'first_name', 'last_name')  # new


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email',)  # new





class HomeForm(forms.ModelForm):
    searchtext = forms.CharField(max_length=150, required=True,
                                 widget=forms.TextInput(attrs={'class': 'form-control',
                                                               'placeholder': 'What are you looking for...'}))

    contributor_author = forms.CharField(max_length=150, required=False,
                                         widget=forms.TextInput(attrs={'class': 'form-control',
                                                                       'placeholder': 'name?'}))

    contributor_department = forms.CharField(max_length=150, required=False,
                                             widget=forms.TextInput(attrs={'class': 'form-control',
                                                                           'placeholder': 'Eg: Computer Science'}))

    contributor_committeechair = forms.CharField(max_length=150, required=False,
                                                 widget=forms.TextInput(attrs={'class': 'form-control',
                                                                               'placeholder': 'Name?'}))

    description_degree = forms.CharField(max_length=150, required=False,
                                         widget=forms.TextInput(attrs={'class': 'form-control',
                                                                       'placeholder': 'PhD,...'}))

    publisher = forms.CharField(max_length=150, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control',
                                                                       'placeholder': 'Eg: Virginia Tech'}))

    date_issued = forms.CharField(max_length=150, required=False,
                                  widget=forms.TextInput(attrs={'class': 'form-control',
                                                                'placeholder': 'Eg: 1999-07-06'}))

    YEARS = [x for x in range(1900, 2500)]
    date1 = forms.DateField(
        label='', widget=forms.SelectDateWidget(years=YEARS))
    date2 = forms.DateField(label='', widget=forms.SelectDateWidget(
        years=YEARS), initial=datetime.date.today)

    class Meta:
        model = SearchResultHistoryModel
        fields = ('searchtext',)


class UploadForm(forms.ModelForm):

    title = forms.CharField(max_length=500, required=True,
                            widget=forms.TextInput(attrs={'class': 'form-control',
                                                          'placeholder': 'Enter your title'})
                            )

    contributor_author = forms.CharField(max_length=500, required=True,
                                         widget=forms.TextInput(attrs={'class': 'form-control',
                                                                       'placeholder': 'Name'})
                                         )

    description_abstract = forms.CharField(max_length=5000, required=True,
                                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                                         'placeholder': 'Abstract'})
                                           )

    contributor_committeechair = forms.CharField(max_length=500, required=True,
                                                 widget=forms.TextInput(attrs={'class': 'form-control',
                                                                               'placeholder': 'Names'})
                                                 )

    contributor_committeemember = forms.CharField(max_length=500, required=True,
                                                  widget=forms.TextInput(attrs={'class': 'form-control',
                                                                                'placeholder': 'Enter namesin quotes (Eg:" Jian Wu" "Ravi Mukkamala" "Michele C. Weigle")'})
                                                  )

    contributor_department = forms.CharField(max_length=500, required=True,
                                             widget=forms.TextInput(attrs={'class': 'form-control',
                                                                           'placeholder': 'Department'})
                                             )

    YEARS = [x for x in range(1940, 2021)]
    date_issued = forms.DateField(label='', widget=forms.SelectDateWidget(
        years=YEARS), initial=datetime.date.today)

    subject = forms.CharField(max_length=500, required=True,
                              widget=forms.TextInput(attrs={'class': 'form-control',
                                                            'placeholder': 'Enter keywords in quotes (Eg: "VSC","SMES","Multi-Level",)'}))

    identifier_sourceurl = forms.CharField(max_length=500, required=True,
                                           widget=forms.TextInput(attrs={'class': 'form-control',
                                                                         'placeholder': 'url'})
                                           )

    file = forms.FileField(required=True)
    handle = forms.CharField(
        max_length=500, required=False, widget=forms.HiddenInput())

    class Meta:
        model = HandleModel
        fields = ('handle',)


class SaveItemForm(forms.ModelForm):
    class Meta:
        model = SaveItemModel
        fields = ('handle',)



#claim form
CAN_YOU_REPRODUCE_CLAIM = [
    ('yes', 'Yes'),
    ('no', 'No'),
    ('partially', 'Partially')
]


class ClaimForm(forms.ModelForm):
    claim_field = forms.CharField(max_length=500, required=True,
                                  help_text="Eg: A reaction chamber for producing hydrogen for fuel cells (100 characters max.)")

    Can_you_reproduce_this_claim = forms.ChoiceField(
        widget=forms.RadioSelect, choices=CAN_YOU_REPRODUCE_CLAIM)

    source_Code = forms.CharField(
        max_length=100, help_text="Enter the URL of your sourcecode", required=False)

    datasets = forms.CharField(
        max_length=100, help_text="Enter the URL of your dataset", required=False)

    experiments_and_results = forms.CharField(
        max_length=1000, widget=forms.Textarea(attrs={'rows': 5}))

    class Meta:
        model = ClaimModel
        fields = ('claim_field',)


class ClaimLikeForm(forms.ModelForm):
    class Meta:
        model = ClaimLikeModel
        fields = ('star', 'handle',)
