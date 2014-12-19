rm mfiles_project/mfiles.db
python manage.py syncdb
python manage.py loaddata dump_data.json
