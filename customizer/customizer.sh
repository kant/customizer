#!/usr/bin/env bash
set -e

# Options
QGEP_UPDATE=NO
while getopts ":u" opt; do
  case $opt in
    n)
      UPDATE=YES
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done
shift $(expr $OPTIND - 1)

CONFIG_FILE=$(realpath $1)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Update QGEP project
if [[ $QGEP_UPDATE =~ YES ]]; then
  echo -e "\e[34mUpdate QGEP project ...\e[39m"
  pushd ../QGEP &> /dev/null
  git pull
  popd &> /dev/null
else
  echo -e "\e[31mQGEP project is not updated.\nUse -u option to automaticaly keep it up to date.\e[39m"
fi

# Reading config (part of congig is needed, remaining is read directly by python)
echo -e "\e[34mreading config in $1 ...\e[39m"
eval "$(${DIR}/../tools/yaml.sh $CONFIG_FILE)"

# QGIS
echo -e "\e[34mopening QGIS to customize the project ...\e[39m"
sed -i -r "s@^original_project = '.*'\$@original_project = '${DIR}/../QGEP/project/qgep_en.qgs'@" ${DIR}/customizer.py
sed -i -r "s@^config_file = '.*'\$@config_file = '${CONFIG_FILE}'@" ${DIR}/customizer.py
sed -i -r "s@^translation_file = '.*'\$@translation_file = '${DIR}/../i18n/translation.yaml'@" ${DIR}/customizer.py
$qgis_bin --nologo --noplugins --noversioncheck --code ${DIR}/customizer.py

# layer relations fix
echo -e "\e[34mfixing relations ...\e[39m"
sed -i -r 's/^(\s*<attributeEditorRelation .*?)relation=""(.*)name="(.*?)"(.*?)$/\1 relation="\3"\2name="\3"\4/g' $output_project


echo -e "\e[32mDone, project customized!\e[39m"
