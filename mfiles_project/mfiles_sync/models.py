# -*- coding: utf-8 -*-

# Import the basic Django ORM models library
from django.db import models
from django.utils import dateparse


class Vault(models.Model):
    name = models.CharField(unique=True, max_length=64)
    guid = models.CharField(max_length=38, blank=True)
    is_enabled = models.BooleanField("enabled?", default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'mfmeta_vault'


class View(models.Model):
    vault = models.ForeignKey(Vault)
    name = models.CharField(max_length=128)
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
    vault = models.ForeignKey(Vault)
    mfiles_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=128)

    MFDatatypeText = 1
    MFDatatypeInteger = 2
    MFDatatypeFloating = 3
    MFDatatypeDate = 5
    MFDatatypeTime = 6
    MFDatatypeTimestamp = 7
    MFDatatypeBoolean = 8
    MFDatatypeLookup = 9
    MFDatatypeMultiSelectLookup = 10
    MFDatatypeInteger64 = 11
    MFDatatypeFILETIME = 12
    MFDatatypeMultiLineText = 13
    MFDatatypeACL = 14

    TextTypes = (MFDatatypeText, MFDatatypeLookup, MFDatatypeMultiSelectLookup,
                 MFDatatypeMultiLineText, MFDatatypeACL)

    IntegerTypes = (MFDatatypeInteger, MFDatatypeInteger64)
    DateTimeTypes = (MFDatatypeDate, MFDatatypeTimestamp)

    TYPE_CHOICES = (
        (MFDatatypeText, 'Text'),
        (MFDatatypeInteger, 'A 32-bit integer'),
        (MFDatatypeFloating, 'A 32-bit integer'),
        (MFDatatypeDate, 'Date'),
        (MFDatatypeTime, 'Time'),
        (MFDatatypeTimestamp, 'Timestamp'),
        (MFDatatypeBoolean, 'Boolean'),
        (MFDatatypeLookup, 'Lookup (from a value list)'),
        (MFDatatypeMultiSelectLookup, 'Multiple selection from a value list'),
        (MFDatatypeInteger64, 'A 64-bit integer. Not used in the properties.'),
        (MFDatatypeFILETIME,
         'FILETIME (a 64-bit integer). Not used in the properties.'),
        (MFDatatypeMultiLineText, 'Multi-line text'),
        (MFDatatypeACL, 'The access control list (ACL).'),
    )

    dtype = models.IntegerField(choices=TYPE_CHOICES)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'mfmeta_propdef'
        unique_together = ("name", "mfiles_id", "vault")


class Property(models.Model):
    pdef = models.ForeignKey(PropertyDef)
    mfiles_display_id = models.CharField(
        max_length=64, db_index=True, null=True)
    txt_value = models.TextField(blank=True)
    int_value = models.IntegerField(null=True)
    float_value = models.FloatField(null=True)
    bool_value = models.NullBooleanField(null=True)
    dt_value = models.DateTimeField(null=True)

    def __unicode__(self):
        return "%s:%s" % (self.value, self.pdef.name)

    class Meta:
        db_table = 'mfmeta_prop'

    def set_value(self, value):
        if self.pdef.dtype in PropertyDef.TextTypes:
            self.txt_value = value
            return

        if self.pdef.dtype in PropertyDef.IntegerTypes:
            self.int_value = value
            return

        if self.pdef.dtype == PropertyDef.MFDatatypeBoolean:
            self.bool_value = value
            return

        if self.pdef.dtype == PropertyDef.MFDatatypeFloating:
            self.float_value = value
            return

        if self.pdef.dtype in PropertyDef.DateTimeTypes:
            # print("=>>> ", value)
            self.dt_value = value
            return

        self.txt_value = str(value)

    def value(self):
        if self.pdef.dtype in PropertyDef.TextTypes:
            return self.txt_value

        if self.pdef.dtype in PropertyDef.IntegerTypes:
            return self.int_value

        if self.pdef.dtype == PropertyDef.MFDatatypeBoolean:
            return self.bool_value

        if self.pdef.dtype == PropertyDef.MFDatatypeFloating:
            return self.float_value
        if self.pdef.dtype in PropertyDef.DateTimeTypes:
            return self.dt_value

        return self.txt_value if self.txt_value else None


class Document(models.Model):
    vault = models.ForeignKey(Vault)
    views = models.ManyToManyField(View, through='DocumentView')
    properties = models.ManyToManyField(Property, through='DocumentProperty')

    mfiles_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=256)
    ext = models.CharField(max_length=8)
    size = models.IntegerField()

    created = models.DateTimeField()
    modified = models.DateTimeField()

    def property(self, name, as_list=False):
        qresult = list(
            self.properties.filter(pdef__name=name)
        )

        if qresult and (qresult[0].pdef.dtype ==
                        PropertyDef.MFDatatypeMultiSelectLookup):
            as_list = True

        result = [p.value() for p in qresult]
        if as_list:
            return result
        else:
            return result[0] if result else None

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
