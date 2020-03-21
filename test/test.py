#!/usr/bin/env python3

from lib.postgres import connectDb
import argparse
import asyncio

argparser = argparse.ArgumentParser(description="execute test cases")
argparser.add_argument(
    '--config-db',
    type=str,
    required=True,
    help="test envrionment database configuration file"
)
argparser.add_argument(
    '--ready-resources',
    type=str,
    required=False,
    help="name of resources which should be ready in the resource table, seperate with ','"
)
args = argparser.parse_args()

# Test and setup database connection
async def test_db_conn():
    print("")
    print('testing database connection')
    (conn, schema) = await connectDb(args.config_db)
    async with conn.cursor() as cur:
        await cur.execute("SELECT 1")
        ret = []
        async for row in cur:
            ret.append(row)
        assert ret == [(1,)]
        print('database connection is OK')
        return (conn, schema)

async def test_resources(conn = None, schema: str = None, names: list = None):
    print("")
    print('testing resources')
    async with conn.cursor() as cur:
        await cur.execute("SELECT name from {}.resource where status = 'ready'".format(schema))
        ret = []
        async for row in cur:
            ret.append(row[0])

        for resource in names:
            exists = False
            for name in ret:
                if name == resource:
                    exists = True
                    break
            if not exists:
                print('Resource {} is missing'.format(resource))
                assert(exists)
        print('resources all exist')

async def main():
    (conn, schema) = await test_db_conn()
    if args.ready_resources:
        await test_resources(conn, schema, args.ready_resources.split(","))
    conn.close()

def execute():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

if __name__ == "__main__":
    execute()