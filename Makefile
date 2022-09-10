shell_plus sp:
	python manage.py shell_plus

migration_visualizer viz:
	python manage.py runscript visualize

clean:
	find  . -name 'migration-dep*' -exec rm {} \;
