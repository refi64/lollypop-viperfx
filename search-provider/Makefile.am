lollypop-sp: lollypop-sp.in Makefile
	$(AM_V_GEN)sed						\
		-e s!\@srcdir\@!$(abs_top_srcdir)!	\
		-e s!\@prefix\@!$(prefix)!		\
		-e s!\@datadir\@!$(datadir)!		\
		-e s!\@pkgdatadir\@!$(pkgdatadir)!	\
		-e s!\@libexecdir\@!$(libexecdir)!	\
		-e s!\@libdir\@!$(libdir)!		\
		-e s!\@pkglibdir\@!$(pkglibdir)!	\
		-e s!\@localedir\@!$(localedir)!	\
		-e s!\@pythondir\@!$(pythondir)!	\
		-e s!\@pyexecdir\@!$(pyexecdir)!	\
		-e s!\@PACKAGE\@!$(PACKAGE)!		\
		-e s!\@VERSION\@!$(VERSION)!		\
		< $< > $@
	chmod a+x $@

org.gnome.Lollypop.SearchProvider.service: org.gnome.Lollypop.SearchProvider.service.in Makefile
	$(AM_V_GEN)sed						\
		-e s!\@srcdir\@!$(abs_top_srcdir)!	\
		-e s!\@prefix\@!$(prefix)!		\
		-e s!\@datadir\@!$(datadir)!		\
		-e s!\@pkgdatadir\@!$(pkgdatadir)!	\
		-e s!\@libexecdir\@!$(libexecdir)!	\
		-e s!\@libdir\@!$(libdir)!		\
		-e s!\@pkglibdir\@!$(pkglibdir)!	\
		-e s!\@localedir\@!$(localedir)!	\
		-e s!\@pythondir\@!$(pythondir)!	\
		-e s!\@pyexecdir\@!$(pyexecdir)!	\
		-e s!\@PACKAGE\@!$(PACKAGE)!		\
		-e s!\@VERSION\@!$(VERSION)!		\
		< $< > $@

searchproviderdir = $(datadir)/gnome-shell/search-providers
searchprovider_DATA = lollypop-search-provider.ini

servicedir = $(datadir)/dbus-1/services
service_DATA = $(service_in_files:.service.in=.service)
service_in_files = org.gnome.Lollypop.SearchProvider.service.in


appdatadir = $(pkgdatadir)
appdata_DATA = lollypop-sp

EXTRA_DIST = \
	$(searchprovider_DATA) \
	$(service_DATA)

CLEANFILES = \
	$(service_DATA)

install-data-hook:
	chmod +x $(pkgdatadir)/lollypop-sp

-include $(top_srcdir)/git.mk
