from mfiles_sync.models import Vault

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from win32com.client import gencache
mfiles = gencache.EnsureModule(
    '{B9C079AA-92DD-4FB4-A0E0-AA3198955B45}', 0, 1, 0
)


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

    def process_view(self, search_ops, obj_ops, mfiles_view, db_view):
        self.stdout.write(str(db_view))
        db_view.condition = (
            mfiles_view.SearchConditions.GetAsExportedSearchString(
                mfiles.constants.MFSearchFlagReturnLatestVisibleVersion
            )
        )
        self.stdout.write(db_view.condition)
        db_view.save()

        conditions = mfiles_view.SearchConditions

        df_date = mfiles.DataFunctionCall()
        df_date.SetDataDate()

        search = mfiles.SearchCondition()
        expression = mfiles.Expression()
        value = mfiles.TypedValue()
        expression.SetPropertyValueExpression(
            mfiles.constants.MFBuiltInPropertyDefLastModified,
            mfiles.constants.MFParentChildBehaviorNone,
            df_date
        )
        value.SetValue(mfiles.constants.MFDatatypeDate, '15/12/2014')

        # expression.SetStatusValueExpression(mfiles.constants.MFStatusTypeObjectID, None)
        # value.SetValue(mfiles.constants.MFDatatypeInteger,0)
        search.Set(
            expression, mfiles.constants.MFConditionTypeGreaterThan, value
        )
        conditions.Add(-1, search)

        objs = search_ops.SearchForObjectsByConditionsEx(
            conditions,
            mfiles.constants.MFSearchFlagReturnLatestVisibleVersion,
            False,
            0
        )

        for objver in objs:
            ext = ''
            for file in objver.Files:
                ext = file.Extension

            self.stdout.write("%s, %s.%s, %d" %
                              (objver.DisplayID, objver.Title,
                               ext, objver.Deleted)
                              )

        # search = mfiles.SearchCondition()
        # expression = mfiles.Expression()
        # value = mfiles.TypedValue()
        # expression.SetStatusValueExpression(mfiles.constants.MFStatusTypeObjectID, None)
        # value.SetValue(mfiles.constants.MFDatatypeInteger,200)
        # search.Set(expression, mfiles.constants.MFConditionTypeLessThanOrEqual, value)
        # conditions.Add(-1, search)

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
                    mfiles_vault.ObjectSearchOperations,
                    mfiles_vault.ObjectOperations,
                    mfiles_view,
                    db_view
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
