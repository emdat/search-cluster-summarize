# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from .models import *
from .forms import *
from .utils import *

# Create your views here.
def index(request):
  if request.method == 'POST':
    form = DomainClusterSearchConfigurationForm(request.POST)
    domain = form.data['domain'].rstrip("/")

    # Get existing DCSC, or None
    try:
      existing_dcsc = DomainClusterSearchConfiguration.objects.get(domain=domain)
      form = DomainClusterSearchConfigurationForm(request.POST, instance=existing_dcsc)
    except DomainClusterSearchConfiguration.DoesNotExist:
      pass

    if form.is_valid():
    # TODO(Emon): Process (ready_for_search)
      dcsc = form.save()
      make_domain_ready_for_search(dcsc)
      return HttpResponseRedirect('/cluster_search/search/')
    else:
      return HttpResponse("Error with form: %s" % form.errors)
  else:
    form = DomainClusterSearchConfigurationForm()
    return render(request, 'cluster_search/index.html', {'form': form}) 

def no_cluster_search(request):
  if request.method == 'POST':
    form = DomainNoClusterSearchQueryForm(request.POST)
    if form.is_valid():
      dcsquery = form.save()
      return HttpResponseRedirect('/cluster_search/%s/%s/no_cluster_results/' % (
                                  dcsquery.domain.domain, dcsquery.query))
    else:
      return HttpResponse("Error with search parameters. Try again.")
  else:
    form = DomainNoClusterSearchQueryForm()
    return render(request, 'cluster_search/no_cluster_search.html', {'form': form}) 

def no_cluster_results(request, domain, query):
  dcsc = DomainClusterSearchConfiguration.objects.get(domain=domain)
  results = get_search_results(dcsc, query)
  return render(request, 'cluster_search/no_cluster_results.html', {'results':results})
  

def search(request):
  if request.method == 'POST':
    form = DomainClusterSearchQueryForm(request.POST)
    if form.is_valid():
      dcsquery = form.save()
      return HttpResponseRedirect('/cluster_search/%s/%s/%s/%s/%s/results/' % ( 
                                  dcsquery.domain.domain,
                                  dcsquery.query,
                                  dcsquery.cluster_algorithm,
                                  dcsquery.summary_algorithm,
                                  dcsquery.rank_algorithm))
    else:
      return HttpResponse("Error with search parameters. Try again.")
  else:
    form = DomainClusterSearchQueryForm()
    return render(request, 'cluster_search/search.html', {'form': form}) 

def results(request, domain, query, cluster_alg, summary_alg, rank_alg):
  dcsc = DomainClusterSearchConfiguration.objects.get(domain=domain)
  clusters = get_clustered_search_results(dcsc, query, cluster_alg, summary_alg, rank_alg)
  return render(request, 'cluster_search/results.html', {'clusters':clusters})
