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

. /etc/init.d/deploy_apps

