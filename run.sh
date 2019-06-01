rm -fr /usr/local/lib/python3.7/site-packages/lollypop/
ninja -C build install
echo "Running lollypop"
lollypop -e
