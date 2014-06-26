# hellotest forms.py

from django import forms


DATA_CHOICES = (
  ('pos', 'Position'),
  ('trc', 'Track'),
)

TX_CHOICES = (
  ('1', '1'),
  ('2', '2'),
)


def get_choices():
  choices_list = tx_ID.objects.all()
  return choices_list

class Form3(forms.Form):
  def __init__(self, *args, **kwargs):
    super(Form3, self).__init__(*args, **kwargs)
    self.fields['tx_ID'] = forms.ChoiceField( choices=get_choices() )


class Form2(forms.Form):
  data_type = forms.ChoiceField(choices=DATA_CHOICES, required=True, label='data_type')
 #tx_ID = forms.ChoiceField(choices=TX_CHOICES, required = True)
  datetime = forms.CharField(max_length = 100, required = True)
  

 # dynamic_field = forms.ModelChoiceField(queryset=Choice.objects.none())
 #   def __init__(self, item_id):
 #     super(Form2, self).__init__)_
 #     self.fields['item_field'].queryset = Item.objects.filter(id=item_id)

 # def __init__(self, *args, **kwargs):
 #   super(Form2, self).__init__(*args, **kwargs)
 #   self.fields['data_type'] = forms.ChoiceField(
 #     choices = get_data_choices() )
  #def __unicode__(self):
  #  return u'%s %s %s' % (self.first, self.last, self.middle)
