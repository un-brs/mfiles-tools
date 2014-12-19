# -*- coding: utf-8 -*-
import datetime
import pycountry

from mfiles_sync import models as sm
from mfiles_docs import models as dm

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from IPython import embed as shell  # noqa

# import logging
# l = logging.getLogger('django.db.backends')
# # l.setLevel(logging.DEBUG)
# l.addHandler(logging.StreamHandler())

UN_NUMBER = "UN-number"
PLAYER = "Player"
TERMS = "Term-ScientificTechnicalPublications"
PROGRAMMES = "Programme/Subject Matter"
CHEMICALS = "Chemical"
CLASSES = ("Class", "Additional classes", "Class groups")


class Command(BaseCommand):
    help = 'Syncronize MFiles documents'

    def add_arguments(self, parser):
        pass

    def process(self, sdoc):
        un_number = sdoc.property(UN_NUMBER)
        doc = None
        if un_number:
            try:
                doc = dm.Document.objects.get(un_number=un_number)
            except ObjectDoesNotExist:
                pass

        if not doc:
            doc = dm.Document(mfiles_id=sdoc.mfiles_id)
            doc.un_number = un_number
            doc.date_publication = sdoc.created
            doc.date_last_update = sdoc.modified
            doc.vault = sdoc.vault.name
            doc.period_start = sdoc.created
            doc.period_end = sdoc.modified

            players = sdoc.property(PLAYER)
            if players:
                countries = ', '.join([pycountry.countries.get(
                    name=p).alpha2 for p in players if p in pycountry.countries.indices['name']])
                authors = ', '.join(
                    [p for p in players if p not in pycountry.countries.indices['name']])

                doc.country = countries
                if authors:
                    doc.author = authors
            try:
                doc.save()
            except Exception:
                self.stderr.write("->" + str(doc) + str(sdoc))
                shell()
                return

            dm.Term.objects.bulk_create(
                [dm.Term(doc=doc, value=term)
                 for term in sdoc.property(TERMS, as_list=True)
                 ]
            )

            dm.Program.objects.bulk_create(
                [dm.Program(doc=doc, value=term)
                 for term in sdoc.property(PROGRAMMES, as_list=True)
                 ]
            )

            dm.Chemical.objects.bulk_create(
                [dm.Program(doc=doc, value=term)
                 for term in sdoc.property(CHEMICALS, as_list=True)
                 ]
            )

            classes = set()
            for cl in CLASSES:
                classes.update(sdoc.property(cl, as_list=True))

            dm.DocType.objects.bulk_create(
                [dm.DocType(doc=doc, value=term)
                 for term in classes
                 ]
            )

        self.process_lang_and_files(sdoc=sdoc, doc=doc)

    def process_lang_and_files(self, sdoc, doc):
        title = sdoc.property('Title')
        description = sdoc.property('Description')

        lang = sdoc.property('Language', as_list=True)[0]

        try:
            lang_alpha2 = pycountry.languages.get(name=lang).alpha2
        except KeyError:
            langs = list(filter(lambda s: s[0].startswith(lang),
                                pycountry.languages.indices['name'].items()
                                ))
            # print(lang, langs, langs[0][1].name)
            lang_alpha2 = langs[0][1].alpha2

        if title:
            try:
                doc.title_set.get(lang=lang_alpha2)
            except ObjectDoesNotExist:
                dm.Title(lang=lang_alpha2, value=title, doc=doc).save()

        if description:
            try:
                doc.description_set.get(lang=lang_alpha2)
            except ObjectDoesNotExist:
                dm.Description(lang=lang_alpha2, value=title, doc=doc).save()

        dm.File(doc=doc, lang=lang_alpha2, ext=sdoc.ext, size=sdoc.size,
                name=sdoc.name).save()

    def handle(self, *args, **options):

        english_docs = sm.Document.objects.filter(
            properties__pdef__name='Language',
            properties__txt_value='English'
        )

        other_docs = sm.Document.objects.exclude(
            properties__pdef__name='Language',
            properties__txt_value='English'
        )

        for sdoc in english_docs:
            self.process(sdoc=sdoc)

        for sdoc in other_docs:
            self.process(sdoc=sdoc)
