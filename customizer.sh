#!/usr/bin/env bash
set -e

# Options
QGEP_UPDATE=NO
CLOSE_QGIS=YES
while getopts ":ud" opt; do
  case $opt in
    u)
      QGEP_UPDATE=YES
      ;;
    d)
      CLOSE_QGIS=NO
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "customizer.sh [-u] [-d] config.yaml"
      echo "  -u update the QGEP project (git submodule update)"
      echo "  -d keep QGIS open at the end of customization for debugging (be careful, relations are broken at this point)"
      exit 1
      ;;
  esac
done
shift $(expr $OPTIND - 1)

if [ ! -f $1 ]; then
  echo -e "\e[31mconfig file does not exist\e[39m" >&2
  exit 1
fi

CONFIG_FILE=$(realpath $1)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Update QGEP project
if [[ $QGEP_UPDATE =~ YES ]]; then
  echo -e "\e[34mUpdate QGEP project ...\e[39m"
  pushd ${DIR}/QGEP &> /dev/null
  git pull
  popd &> /dev/null
else
  echo -e "\e[31mQGEP project is not updated.\nUse -u option to automaticaly keep it up to date.\e[39m"
fi

# Reading config (part of congig is needed, remaining is read directly by python)
echo -e "\e[34mreading config in $1 ...\e[39m"
eval "$(${DIR}/tools/yaml.sh $CONFIG_FILE)"

# Tweaks
echo -e "\e[34mTweaking python scripts by sed commands ...\e[39m"
sed -i -r "s@^original_project = '.*'\$@original_project = '${DIR}/QGEP/project/qgep_en.qgs'@" ${DIR}/customizer.py
sed -i -r "s@^config_file = '.*'\$@config_file = '${CONFIG_FILE}'@" ${DIR}/customizer.py
sed -i -r "s@^translation_file = '.*'\$@translation_file = '${DIR}/i18n/fr.yaml'@" ${DIR}/customizer.py
sed -i -r "s@^symbology_macro_file = '.*'\$@symbology_macro_file = '${DIR}/macros_symbology.py'@" ${DIR}/customizer.py
if [[ $CLOSE_QGIS =~ YES ]]; then
  sed -i -r 's/^[#]?QgsApplication\.exitQgis\(\)/QgsApplication.exitQgis()/' ${DIR}/customizer.py
else
  sed -i -r 's/^[#]?QgsApplication\.exitQgis\(\)/#QgsApplication.exitQgis()/' ${DIR}/customizer.py
fi
sed -i -r "s@^style_file = '.*'\$@style_file = '${style_file}'@" ${DIR}/macros_symbology.py

# QGIS
echo -e "\e[34mopening QGIS to customize the project ...\e[39m"
set +e # QGIS seg faults, but no issue on project
$qgis_bin --nologo --noplugins --noversioncheck --code ${DIR}/customizer.py &> /dev/null
set -e

# layer relations fix
echo -e "\e[34mfixing relations ...\e[39m"
sed -i -r 's/^(\s*<attributeEditorRelation .*?)relation=""(.*)name="(.*?)"(.*?)$/\1 relation="\3"\2name="\3"\4/g' $output_project
echo -e "\e[32mDone, project customized!\e[39m"

if [[ $CLOSE_QGIS =~ YES ]]; then
  echo -e "\e[34mopening QGIS with customized project\e[39m"
  $qgis_bin $output_project &
fi
