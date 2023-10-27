#! /bin/bash

ROLE_NAME="OasisDefenderRole"
USER_NAME="OasisDefenderUser"
SERVICE_NAME="OasisDefender_sp"

account_info=$(az account show)
sub_name=$(echo $account_info | jq -r .name)
sub_id=$(echo $account_info | jq -r .id)

echo "Your current subscription is ${sub_name} / ${sub_id}"
read -p "Is this the subscription you want to use? [y/n] " -n 1

if [ "$REPLY" == "n" ]; then
    all_sub=$(az account list)
    sub_list=$(echo $all_sub | jq -r '.[].name')
    tmp_id_list=$(echo $all_sub | jq -r '.[].id')
    id_list=($tmp_id_list)
    echo "Select your subscription:"
    IFS=$'\n'
    num=0
    for i in $sub_list; do
        echo "($num) $i / ${id_list[$num]}"
        num=$(( $num + 1 ))
    done
    num=$(($num-1))
    read -p "Enter number from 0 - $num: " sub_selection
    tmp_sub_list=($sub_list)
    echo "Setting the subscription to ${tmp_sub_list[$sub_selection]} / ${id_list[$sub_selection]}"
    az account set --subscription ${id_list[$sub_selection]} --only-show-errors
    account_info=$(az account show -s ${id_list[$sub_selection]})
    sub_name=$(echo $account_info | jq -r .name)
    sub_id=$(echo $account_info | jq -r .id)
    unset IFS
fi

tenant_id=$(echo $account_info | jq -r .tenantId)

echo
echo Create Custom Role $ROLE_NAME
cat > /tmp/oaz_role.json <<- EOF
{
    "Name": "$ROLE_NAME",
    "Description": "Role used by Oasis Defender",
    "IsCustom": true,
    "Actions": [
        "*/read"
    ],
    "AssignableScopes": [
        "/subscriptions/$sub_id"
    ]
}
EOF
oaz_role=$(az role definition create --subscription $sub_id --role-definition /tmp/oaz_role.json 2>&1)
rm /tmp/oaz_role.json

echo
echo Create Service principle $SERVICE_NAME
oaz_sp=$(az ad sp create-for-rbac -n $SERVICE_NAME --role $ROLE_NAME --scopes /subscriptions/$sub_id)

app_id=$(echo $oaz_sp | jq -r '.appId')
if [ "$app_id" = "null" ]; then
    echo "Cannot create service principle, running script again after checking permissions"
    echo $oaz_sp
    exit 1
fi

disp_name=$(echo $oaz_sp | jq -r .displayName)
password=$(echo $oaz_sp | jq -r .password)
tenant_id=$(echo $oaz_sp | jq -r .tenant)

echo
echo "----------------------------------------------------------------------------------------------------"
echo "          Tenant: $tenant_id"
echo "    Subscription: $sub_id"
echo "             App: $app_id"
echo "          Secret: $password"
echo "----------------------------------------------------------------------------------------------------"
echo
