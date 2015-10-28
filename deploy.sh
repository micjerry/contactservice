#!/bin/bash

#the name of app
APP_NAME="app_contact"

#the github path of app
APP_GIT_PATH="https://github.com/micjerry/contactservice.git"

#the root path of app
ROOT_PATH="/opt/webapps"
APP_PATH="${ROOT_PATH}/${APP_NAME}"
START_PORT=8000

CONF_ROOT_PATH="/etc/mx_apps"
APP_CONF_PATH="${CONF_ROOT_PATH}/${APP_NAME}"
PORT_FLAG="{port}"
INSTANCE_FLAG="{instance}"

AUTO_START_SC="contact-server"

TMP_GIT_PATH="/opt/tempgit"

usage()
{
  echo "Usage: $0 {deploy|commit}"
  exit 0
}

die()
{
  echo $1
  exit 1
}

deploy_instance()
{
  local port_num=$[$START_PORT+$1] 
  local instanse_id=$[$1+1]
  [ -d ${APP_CONF_PATH} ] || mkdir -p ${APP_CONF_PATH}
  local instance_conf="${APP_CONF_PATH}/${APP_NAME}_is${instanse_id}.conf"
  echo "port = ${port_num}" > ${instance_conf}
  echo "pidfile = \"/var/run/${APP_NAME}_is${instanse_id}.pid\"" >> ${instance_conf}
  echo "logfile = \"/var/log/${APP_NAME}_is${instanse_id}\"" >> ${instance_conf}
  
  #auto start
  chkconfig --add $AUTO_START_SC
  chkconfig --level 345 $AUTO_START_SC on
}

download_app()
{
  [ -d ${TMP_GIT_PATH} ] || mkdir -p ${TMP_GIT_PATH}
  cd ${TMP_GIT_PATH} >/dev/null 2>&1
  git clone ${APP_GIT_PATH}
  local git_dir=`echo ${APP_GIT_PATH##*/} | sed 's/.git//'`
  local git_path="${TMP_GIT_PATH}/${git_dir}"
  
  [ ! -d $git_path ] && die "download app failed"

  #init app path and copy all the code
  [ -d ${APP_PATH} ] || mkdir -p ${APP_PATH}
  cp -f $git_path/*.py ${APP_PATH}
  find $git_path -maxdepth 1 -mindepth 1 -type d | sed '/\.git/d' > /tmp/appdirs.txt
  while read line;
  do
    local sub_dir=`echo ${line##*/}`
    mkdir -p "${APP_PATH}/${sub_dir}"
    cp -f "$git_path/${sub_dir}/*.py" "${APP_PATH}/${sub_dir}"
  done < /tmp/appdirs.txt

  [ -f "$git_path/${AUTO_START_SC}" ] && cp -f "$git_path/${AUTO_START_SC}" /etc/init.d

  #clen temp file
  [ -d $git_path ] && rm -rf $git_path
}

deploy()
{
  #check deploy process numbers
  local depct=1
  [ -n "$1" ] && depct=$1
  cpu_count=`grep processor /proc/cpuinfo | wc -l`
  if [ $depct -gt $cpu_count ]; then
    depct=$cpu_count
  fi

  download_app

  for((i=0;i<${depct};i++))
  do
    deploy_instance "$i"
  done
}

case "$1" in
  deploy)
    deploy $2
    ;;
  commit)
    commit
    ;;
  * )
    usage
    ;;
esac

