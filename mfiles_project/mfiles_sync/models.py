# -*- coding: utf-8 -*-

# Import the basic Django ORM models library
from django.db import models


class Vault(models.Model):
    name = models.CharField(unique=True, max_length=64)
    guid = models.CharField(unique=True, max_length=38, blank=True)
    is_enabled = models.BooleanField("enabled?", default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'mfmeta_vault'


class View(models.Model):
    name = models.CharField(max_length=128)
    vault = models.ForeignKey(Vault)
    condition = models.TextField()
    is_enabled = models.BooleanField("enabled?", default=True)

    def __str__(self):
        return "%s, vault=%s" % (
            self.name, str(self.vault))

    class Meta:
        db_table = 'mfmeta_view'


class ViewSync(models.Model):
    view = models.ForeignKey(View)
    date_sync_start = models.DateTimeField()
    date_sync_end = models.DateTimeField()
    status = models.IntegerField(blank=True)

    def __unicode__(self):
        return ("ViewSync<view=%s, start=%s, end=%s, status=%d>" %
                (str(self.view),
                 str(self.date_sync_start),
                 str(self.date_sync_end))
                )

    class Meta:
        db_table = 'mfmeta_viewsync'


class PropertyDef(models.Model):
    mfiles_id = models.IntegerField()
    name = models.CharField(max_length=128)
    vault = models.ForeignKey(Vault)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'mfmeta_propdef'
        unique_together = ("name", "mfiles_id", "vault")


class Property(models.Model):
    mfiles_id = models.IntegerField(null=True)
    txt_value = models.TextField(blank=True)
    int_value = models.IntegerField(null=True)
    float_value = models.FloatField(null=True)
    bool_value = models.NullBooleanField(null=True)
    dt_value = models.DateTimeField()

    pdef = models.ForeignKey(PropertyDef)

    def __unicode__(self):
        return "%s:%s" % (self.value, self.pdef.name)

    class Meta:
        db_table = 'mfmeta_prop'


class Document(models.Model):
    mfiles_id = models.IntegerField()
    views = models.ManyToManyField(View, through='DocumentView')
    properties = models.ManyToManyField(Property, through='DocumentProperty')

    ext = models.CharField(max_length=8)
    size = models.IntegerField()

    created = models.DateTimeField()
    modified = models.DateTimeField()

    def __unicode__(self):
        return self.name + (".%s" % self.ext if self.ext else "")

    class Meta:
        db_table = 'mfmeta_doc'


class DocumentView(models.Model):
    doc = models.ForeignKey(Document)
    view = models.ForeignKey(View)

    class Meta:
        unique_together = ("doc", "view")
        db_table = 'mfmeta_docview'


class DocumentProperty(models.Model):
    doc = models.ForeignKey(Document)
    prop = models.ForeignKey(Property)

    class Meta:
        unique_together = ("doc", "prop")
        db_table = 'mfmeta_docprop'
