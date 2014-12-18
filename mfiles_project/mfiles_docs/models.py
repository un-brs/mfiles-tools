# -*- coding: utf-8 -*-

# Import the basic Django ORM models library
from django.db import models


class Document(models.Model):
    mfiles_id = models.IntegerField()
    vault = models.CharField(max_length=64)
    un_number = models.CharField(max_length=128, blank=True)
    date_publication = models.DateTimeField()
    date_last_update = models.DateTimeField()
    period_start = models.DateTimeField(null=True)
    period_end = models.DateTimeField(null=True)
    copyright = models.CharField(max_length=256, blank=True)
    author = models.CharField(max_length=256, blank=True)
    meeting = models.CharField(max_length=256, blank=True)
    country = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return ("Document<mfiles_id=%d, un_number=%s>" %
                (self.mfiles_id, self.un_number))

    class Meta:
        db_table = 'mfdoc_doc'
        unique_together = ("mfiles_id", "vault")


class DocType(models.Model):
    doc = models.ForeignKey(Document)
    value = models.TextField()

    def __str__(self):
        return ("DocType<doc=%d, value=%s>" %
                (self.doc, self.value))

    class Meta:
        db_table = 'mfdoc_doctype'


class Chemical(models.Model):
    doc = models.ForeignKey(Document)
    value = models.CharField(max_length=512)

    def __str__(self):
        return ("Chemical<doc=%d, value=%s>" %
                (self.doc, self.value))

    class Meta:
        db_table = 'mfdoc_chemical'
        unique_together = ("doc", "value")


class Term(models.Model):
    doc = models.ForeignKey(Document)
    value = models.CharField(max_length=512)

    def __str__(self):
        return ("Term<doc=%d, value=%s>" %
                (self.doc, self.value))

    class Meta:
        db_table = 'mfdoc_term'
        unique_together = ("doc", "value")


class Program(models.Model):
    doc = models.ForeignKey(Document)
    value = models.TextField()

    def __str__(self):
        return ("Program<doc=%d, value=%s>" %
                (self.doc, self.value))

    class Meta:
        db_table = 'mfdoc_program'


class Title(models.Model):
    doc = models.ForeignKey(Document)
    lang = models.CharField(max_length=8)
    value = models.CharField(max_length=512)

    def __str__(self):
        return ("Title<doc=%d, lang=%s, value=%s>" %
                (self.doc, self.lang, self.value))

    class Meta:
        db_table = 'mfdoc_title'
        unique_together = ("doc", "lang")


class Description(models.Model):
    doc = models.ForeignKey(Document)
    lang = models.CharField(max_length=8)
    value = models.TextField()

    def __str__(self):
        return ("Description<doc=%d, lang=%s, value=%s>" %
                (self.doc, self.lang, self.value))

    class Meta:
        db_table = 'mfdoc_desc'
        unique_together = ("doc", "lang")


class File(models.Model):
    doc = models.ForeignKey(Document)
    lang = models.CharField(max_length=8)
    name = models.CharField(max_length=255)
    ext = models.CharField(max_length=8)
    size = models.IntegerField()

    class Meta:
        db_table = 'mfdoc_file'
        unique_together = ("doc", "lang", "name", "ext")
