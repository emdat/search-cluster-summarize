from django import forms
from cluster_search.models import DomainClusterSearchConfiguration, DomainClusterSearchQuery

class DomainClusterSearchConfigurationForm(forms.ModelForm):
  mysql_password = forms.CharField(required=False)
  
  class Meta:
    model = DomainClusterSearchConfiguration
    exclude = ['last_updated']

  def clean_domain(self):
    domain_content = self.cleaned_data.get('domain')
    return domain_content.rstrip("/")

class DomainClusterSearchQueryForm(forms.ModelForm):
  domain = forms.ModelChoiceField(queryset=DomainClusterSearchConfiguration.objects, empty_label=None)
  class Meta:
    model = DomainClusterSearchQuery
    fields = '__all__'

class DomainNoClusterSearchQueryForm(forms.ModelForm):
  domain = forms.ModelChoiceField(queryset=DomainClusterSearchConfiguration.objects, empty_label=None)
  class Meta:
    model = DomainClusterSearchQuery
    fields = ['domain', 'query']
