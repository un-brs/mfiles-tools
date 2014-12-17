# -*- coding: utf-8 -*-
import datetime
import calendar
import sys


from mfiles_sync.models import (Vault, Document, DocumentView, PropertyDef,
                                Property, DocumentProperty)

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from win32com.client import gencache
mfiles = gencache.EnsureModule(
    '{B9C079AA-92DD-4FB4-A0E0-AA3198955B45}', 0, 1, 0
)


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    # print(year, month)
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


class Command(BaseCommand):
    help = 'Syncronize MFiles'

    def add_arguments(self, parser):
        pass

    def get_server_vaults(self):
        server = mfiles.MFilesServerApplication()
        server.Connect(AuthType=mfiles.constants.MFAuthTypeSpecificMFilesUser,
                       UserName=settings.MFILES_USERNAME,
                       Password=settings.MFILES_PASSWORD,
                       NetworkAddress=settings.MFILES_HOST,
                       Endpoint="2266")
        return server.GetVaults()

    def process_valuelist(self, db_pdef, mfiles_valuelist):
        for mfiles_item in mfiles_valuelist:
            print
            db_prop = Property(
                mfiles_display_id=mfiles_item.DisplayID, pdef=db_pdef)
            db_prop.set_value(mfiles_item.Name)
            db_prop.save()

    def process_propertydef(self, mfiles_pdef, mfiles_vault, db_vault):
        db_pdefs = list(
            PropertyDef.objects.filter(
                mfiles_id=mfiles_pdef.ID, vault=db_vault)
        )

        if db_pdefs:
            db_pdef = db_pdefs[0]
        else:
            db_pdef = PropertyDef(
                name=mfiles_pdef.Name,
                mfiles_id=mfiles_pdef.ID,
                vault=db_vault,
                dtype=mfiles_pdef.DataType
            )
            db_pdef.save()
            if mfiles_pdef.ValueList:
                self.process_valuelist(
                    db_pdef=db_pdef,
                    mfiles_valuelist=mfiles_vault.ValueListItemOperations.GetValueListItems(
                        mfiles_pdef.ValueList
                    )
                )

        return db_pdef

    def process_property(self, mfiles_typedvalue, db_pdef, db_doc):
        if db_pdef.dtype in (PropertyDef.MFDatatypeMultiSelectLookup,
                             PropertyDef.MFDatatypeLookup):
            for lookup in mfiles_typedvalue.GetValueAsLookups():
                db_props = list(
                    db_pdef.property_set.filter(
                        mfiles_display_id=lookup.DisplayID
                    )
                )
                if db_props:
                    db_prop = db_props[0]
                    db_docprop = DocumentProperty(doc=db_doc, prop=db_prop)
                    db_docprop.save()
        else:
            if mfiles_typedvalue.Value:
                db_prop = Property(pdef=db_pdef)
                db_prop.set_value(mfiles_typedvalue.Value)
                db_prop.save()

                db_docprop = DocumentProperty(doc=db_doc, prop=db_prop)
                db_docprop.save()

    def process_properties(self, mfiles_props, mfiles_vault, db_vault, db_doc):
        for mfiles_prop in mfiles_props:
            mfiles_pdef = mfiles_vault.PropertyDefOperations.GetPropertyDef(
                mfiles_prop.PropertyDef
            )
            self.stdout.write(mfiles_pdef.Name)
            db_pdef = self.process_propertydef(
                mfiles_pdef=mfiles_pdef,
                mfiles_vault=mfiles_vault,
                db_vault=db_vault
            )

            self.process_property(
                mfiles_typedvalue=mfiles_prop.Value,
                db_pdef=db_pdef,
                db_doc=db_doc
            )

            # if pdef.ValueList:
            #     lst = [item.Name for item in mfiles_vault.ValueListItemOperations.GetValueListItems(
            #         mfiles_pdef.ValueList)]
            #         self.stdout.write(", ".join(lst))
            #     except Exception as e:
            #         self.stdout.write(self.stdout.encoding)
            # print(lst)
            #         sys.exit(1)

            # if pdef.Name not in properties:
            #     prop = {"count": 0, "type": datatype_to_str[pdef.DataType]}
            #     if pdef.ValueList:
            #         prop["values"] = dict(
            #             [(item.Name, 0) for item in vault.ValueListItemOperations.GetValueListItems(pdef.ValueList)])
            #     properties[pdef.Name] = prop
            # else:
            #     prop = properties[pdef.Name]

            # if p.GetValueAsUnlocalizedText():
            #     prop["count"] += 1
            #     if pdef.ValueList:
            #         for lookup in p.Value.GetValueAsLookups():
            #             if lookup.DisplayValue not in prop["values"]:
            #                 prop["values"][lookup.DisplayValue] = 0
            #             prop["values"][lookup.DisplayValue] += 1

    def process_object_version(self, mfiles_vault, object_version, db_view,
                               db_vault):
        if object_version.FilesCount != 1:
            self.stderr.write(
                "'%s' does not contains files" % object_version.Title
            )
            return

        db_doc = Document(mfiles_id=object_version.ObjVer.ID)
        file = object_version.Files.Item(1)

        db_doc.name = file.Title
        db_doc.ext = file.Extension
        db_doc.size = file.LogicalSize

        db_doc.created = object_version.CreatedUtc
        db_doc.modified = object_version.LastModifiedUtc
        db_doc.save()

        db_docview = DocumentView(doc=db_doc, view=db_view)
        db_docview.save()

        mfiles_props = (
            mfiles_vault.ObjectOperations.GetObjectVersionAndProperties(
                object_version.ObjVer
            ).Properties
        )

        self.process_properties(
            mfiles_vault=mfiles_vault,
            mfiles_props=mfiles_props,
            db_vault=db_vault,
            db_doc=db_doc
        )

    def process_view(self, mfiles_vault, mfiles_view, db_view, db_vault):
        self.stdout.write(str(db_view))
        db_view.condition = (
            mfiles_view.SearchConditions.GetAsExportedSearchString(
                mfiles.constants.MFSearchFlagReturnLatestVisibleVersion
            )
        )
        db_view.save()

        conditions = mfiles_view.SearchConditions

        df_date = mfiles.DataFunctionCall()
        df_date.SetDataDate()

        # ======================================================================
        search = mfiles.SearchCondition()
        expression = mfiles.Expression()
        value = mfiles.TypedValue()
        expression.SetPropertyValueExpression(
            mfiles.constants.MFBuiltInPropertyDefLastModified,
            mfiles.constants.MFParentChildBehaviorNone,
            df_date
        )
        # value.SetValue(mfiles.constants.MFDatatypeDate, '15/12/2014')
        search.Set(
            expression, mfiles.constants.MFConditionTypeGreaterThanOrEqual, value
        )
        conditions.Add(-1, search)
        # ======================================================================
        search = mfiles.SearchCondition()
        expression = mfiles.Expression()
        # value = mfiles.TypedValue()
        expression.SetPropertyValueExpression(
            mfiles.constants.MFBuiltInPropertyDefLastModified,
            mfiles.constants.MFParentChildBehaviorNone,
            df_date
        )
        # value.SetValue(mfiles.constants.MFDatatypeDate, '15/12/2014')
        search.Set(
            expression, mfiles.constants.MFConditionTypeLessThan, value
        )
        conditions.Add(-1, search)
        # ======================================================================

        start = datetime.date(2014, 12, 1)
        end = add_months(start, 1)

        while start < datetime.date.today():
            print("Process date range", start, end)

            conditions.Item(conditions.Count - 1).TypedValue.SetValue(
                mfiles.constants.MFDatatypeDate, start.strftime('%d/%m/%Y')
            )
            conditions.Item(conditions.Count).TypedValue.SetValue(
                mfiles.constants.MFDatatypeDate, end.strftime('%d/%m/%Y')
            )

            objs = mfiles_vault.ObjectSearchOperations.SearchForObjectsByConditionsEx(
                conditions,
                mfiles.constants.MFSearchFlagReturnLatestVisibleVersion,
                False,
                0
            )

            for object_version in objs:
                self.process_object_version(
                    mfiles_vault=mfiles_vault,
                    object_version=object_version,
                    db_view=db_view,
                    db_vault=db_vault
                )

            start, end = end, add_months(start, 1)

    def process_vault(self, mfiles_vault, db_vault):
        self.stdout.write('Vault %s %s' % (db_vault.name,
                                           mfiles_vault.GetGUID()))
        db_vault.guid = mfiles_vault.GetGUID()
        db_vault.save()

        mfiles_views = {
            v.Name: v for v in mfiles_vault.ViewOperations.GetViews()
        }

        for db_view in db_vault.view_set.filter(is_enabled=True):
            mfiles_view = mfiles_views.get(db_view.name)
            if mfiles_view:
                self.process_view(
                    mfiles_vault=mfiles_vault,
                    mfiles_view=mfiles_view,
                    db_view=db_view,
                    db_vault=db_vault
                )
            else:
                self.stdout.write("Could not find view '%s'" % db_view.name)

    def handle(self, *args, **options):
        mfiles_svaults = {v.Name: v for v in self.get_server_vaults()}

        for db_vault in Vault.objects.filter(is_enabled=True):
            mfiles_svault = mfiles_svaults.get(db_vault.name)
            if mfiles_svault:
                mfiles_vault = mfiles_svault.LogIn()
                if mfiles_vault.LoggedIn:
                    self.process_vault(mfiles_vault, db_vault)
                else:
                    self.stderr.write("Could not login to '%s' vault " %
                                      db_vault.name)
            else:
                self.stderr.write("Could not find vault %s" % db_vault.name)
