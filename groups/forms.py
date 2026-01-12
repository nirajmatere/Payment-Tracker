from django import forms
from .models import GroupExpense, groups
from django.contrib.auth.models import User

class GroupForm(forms.ModelForm):
    class Meta:
        model = groups
        fields = ['name', 'group_image', 'users']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter group name'}),
            'group_image': forms.FileInput(attrs={'class': 'form-control'}),
            'users': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['users'].label_from_instance = lambda obj: f"{obj.username} ({obj.email})" if obj.email else obj.username


class GroupExpenseForm(forms.ModelForm):
    # This form will need to be dynamically populated with group members in the view
    split_type = forms.ChoiceField(
        choices=[('EQUAL', 'Split Equally'), ('EXACT', 'Split by Exact Amount')],
        widget=forms.RadioSelect,
        initial='EQUAL'
    )
    paid_by = forms.ModelChoiceField(queryset=User.objects.none(), label="Paid By")

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super(GroupExpenseForm, self).__init__(*args, **kwargs)
        if group:
            self.fields['paid_by'].queryset = group.users.all()
        
        # Add basic styling to paid_by
        self.fields['paid_by'].widget.attrs.update({'class': 'form-select'})

    class Meta:
        model = GroupExpense
        fields = ['description', 'amount', 'currency', 'paid_by']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What was this for?'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
        }
