project('lollypop',
  version: '0.9.243',
  meson_version: '>= 0.40.0'
)
i18n = import('i18n')
python = import('python3')
project_id = 'org.gnome.Lollypop'

message('Looking for dependencies')
dependency('python3')
dependency('glib-2.0')
dependency('gobject-introspection-1.0', version: '>=1.35.9')
dependency('gtk+-3.0', version :'>=3.14')

python_dir = join_paths(get_option('prefix'), python.sysconfig_path('purelib'))
LIBEXEC_DIR = join_paths(get_option('prefix'), 'libexec')
DATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

conf = configuration_data()
conf.set('PACKAGE_URL', 'https://github.com/gnumdk/lollypop')
conf.set('DATA_DIR', DATA_DIR)
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
conf.set('PYTHON_DIR', python_dir)
conf.set('PYTHON_EXEC_DIR', join_paths(get_option('prefix'), python.sysconfig_path('stdlib')))
conf.set('libexecdir', LIBEXEC_DIR)
conf.set('VERSION', meson.project_version())

subdir('data')
subproject('po')
subproject('help')
subdir('search-provider')

install_subdir(
  'lollypop',
  install_dir: python_dir
)

message('Preparing init file')
configure_file(
  input: 'lollypop.in',
  output: 'lollypop',
  configuration: conf,
  install_dir: 'bin'
)

configure_file(
  input: 'lollypop-cli.in',
  output: 'lollypop-cli',
  configuration: conf,
  install_dir: 'bin'
)

meson.add_install_script('meson_post_install.py')
