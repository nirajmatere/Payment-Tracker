from django import forms
from .models import GroupExpense
from django.contrib.auth.models import User

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
