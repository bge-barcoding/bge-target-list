docker run --rm -p 8888:8888 --user=root -e NB_UID=`id -u` -v "${PWD}":/home/jovyan/work jupyter/scipy-notebook:latest