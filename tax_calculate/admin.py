from django.contrib import admin

from tax_calculate.models import TaxCalculation,FAQ
admin.site.register(TaxCalculation) 
admin.site.register(FAQ)
# Register your models here.
