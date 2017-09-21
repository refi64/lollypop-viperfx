#!/bin/bash

function generate_resource()
{
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<gresources>'
    echo '  <gresource prefix="/org/gnome/Lollypop">'
    for file in data/*.css
    do
        echo -n '    <file compressed="true">'
        echo -n $(basename $file)
        echo '</file>'
    done
    for file in data/*.ui AboutDialog.ui
    do
        echo -n '     <file compressed="true" preprocess="xml-stripblanks">'
        echo -n $(basename $file)
        echo '</file>'
    done
    echo '  </gresource>'
    echo '</gresources>'
}

function generate_pot()
{
    echo '[encoding: UTF-8]'
    for file in data/*.xml data/*.in lollypop/*.py
    do
        echo ../$file
    done
    for file in data/*.ui data/AboutDialog.ui.in
    do
        echo -n '[type: gettext/glade]'
        echo ../$file
    done
}

generate_resource > data/lollypop.gresource.xml
generate_pot > subprojects/po/POTFILES.in
