if [[ "`which psql`" == "" ]]; then
    echo "Executive psql not found"
    exit 1
fi

USER="sardines"
PASSWORD="Sardines2019"
DATABASE="sardines_test"
SCHEMA="test"
HOST="localhost"
PORT=5432

psql -h $HOST -p $PORT  -c "CREATE DATABASE $DATABASE;"
psql -h $HOST -p $PORT -d $DATABASE -c "CREATE USER $USER WITH PASSWORD \"$PASSWORD\";"
psql -h $HOST -p $PORT -d $DATABASE -c "GRANT ALL PRIVILEGES ON DATABASE $DATABASE TO $USER;"
psql -h $HOST -p $PORT -d $DATABASE -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
PGPASSWORD=$PASSWORD psql -h $HOST -p $PORT -U $USER -d $DATABASE -c "CREATE SCHEMA IF NOT EXISTS $SCHEMA;"
PGPASSWORD=$PASSWORD psql -h $HOST -p $PORT -U $USER -d $DATABASE -c "SELECT uuid_generate_v4();"
