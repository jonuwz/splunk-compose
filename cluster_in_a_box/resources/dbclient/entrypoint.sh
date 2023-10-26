#!/bin/bash 

echo $DBHOST $DBUSER $DBPASSWORD $DBNAME

while true;do

myr=$(echo $RANDOM | md5sum | head -c 20)
mysql --host=$DBHOST --user=$DBUSER --password=$DBPASSWORD $DBNAME << EOF
insert into stuff values(0,'$myr');
EOF

sleep 1
done

