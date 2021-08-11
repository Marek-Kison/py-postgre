import json
from configparser import ConfigParser
import psycopg2
from psycopg2.extras import Json

configuration = 'frinx-uniconfig-topology:configuration'
intrafaces = 'openconfig-interfaces:interfaces'
cisco = 'Cisco-IOS-XE-native:native'
PORT_CHANNEL = 'Port-channel'
TEN_GIGABIT = 'TenGigabitEthernet'
ONE_GIGABIT = 'GigabitEthernet'


def config(filename='database.ini', section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(
            'Section {0} not found in the {1} file'.format(section, filename))

    return db


def create_table():
    comand = (
        """
        CREATE TABLE IF NOT EXISTS test (
            id SERIAL PRIMARY KEY,
    	    connection INTEGER,
    	    name VARCHAR(255) NOT NULL,
    	    description VARCHAR(255),
    	    config json,
    	    type VARCHAR(50),
    	    infra_type VARCHAR(50),
    	    port_channel_id INTEGER,
    	    max_frame_size INTEGER
        )
        """
    )

    connection = None
    try:
        params = config()
        connection = psycopg2.connect(**params)
        print("Connected to database")
        cursor = connection.cursor()
        cursor.execute(comand)
        cursor.close()
        connection.commit()

    except (Exception, psycopg2.DatabaseError) as e:
        print(e)
    finally:
        if connection is not None:
            connection.close()


def insert_data(database_list):
    """ Insert data into database"""
    sql = """ INSERT INTO test (name, description, config,port_channel_id,max_frame_size) 
                       VALUES (%s,%s,%s,%s,%s) """
    connection = None

    try:
        params = config()
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()
        cursor.executemany(sql, database_list)
        connection.commit()
        print(cursor.rowcount, "Record inserted successfully")
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if connection is not None:
            connection.close()


with open('config.json') as json_data:
    record_list = json.load(json_data)

    find_names = record_list[configuration][intrafaces]['interface']
    list_of_names = [x['name'] for x in find_names]
    # print(list_of_names)

    description_list = []
    for i in range(len(find_names)):
        config_path = find_names[i]['config']
        if 'description' in config_path:
            description_list.append(config_path['description'])
        else:
            description_list.append(None)

    # * TenGigabit
    ten_gigabit_config = record_list[configuration][cisco]['interface'][TEN_GIGABIT]

    ten_gigabit_names = [TEN_GIGABIT + x['name']
                         for x in ten_gigabit_config]
    ten_gigabit_desription = [x['description']
                              for x in ten_gigabit_config]
    ethernet_to_port_group = 'Cisco-IOS-XE-ethernet:channel-group'
    ten_gigabit_mtu, ten_channel_group = [], []
    for i in range(len(ten_gigabit_config)):
        mtus = ten_gigabit_config[i]
        if 'mtu' in mtus:
            ten_gigabit_mtu.append(mtus['mtu'])
        else:
            ten_gigabit_mtu.append(None)
        if ethernet_to_port_group in mtus:
            ten_channel_group.append(mtus[ethernet_to_port_group]['number'])
        else:
            ten_channel_group.append(None)

    ten_channel_group_json = json.dumps(ten_channel_group)

    # * Gigabit
    one_gigabit_config = record_list[configuration][cisco]['interface'][ONE_GIGABIT]
    one_gigabit_names, one_gigabit_desription, one_gigabit_mtu = [], [], []
    for i in range(len(one_gigabit_config)):
        names = one_gigabit_config[i]
        if 'name' in names:
            one_gigabit_names.append(ONE_GIGABIT + names['name'])
        else:
            one_gigabit_names.append(None)
        if 'description' in names:
            one_gigabit_desription.append(names['description'])
        else:
            one_gigabit_desription.append(None)
        if 'mtu' in names:
            one_gigabit_mtu.append(names['mtu'])
        else:
            one_gigabit_mtu.append(None)

    # * Port-channel
    port_channel_config = record_list[configuration][cisco]['interface'][PORT_CHANNEL]
    port_channel_names, port_channel_desription, port_channel_mtu = [], [], []
    for i in range(len(port_channel_config)):
        names = port_channel_config[i]
        if 'name' in names:
            port_channel_names.append(PORT_CHANNEL + str(names['name']))
        else:
            port_channel_names.append(None)

        if 'description' in names:
            port_channel_desription.append(names['description'])
        else:
            port_channel_desription.append(None)

        if 'mtu' in names:
            port_channel_mtu.append(names['mtu'])
        else:
            port_channel_mtu.append(None)

    # * BDI
    bdi_config = record_list[configuration][cisco]['interface']['BDI']
    bdi_names = [x['name'] for x in bdi_config]
    bdi_desc = []
    for i in range(len(bdi_config)):
        names = bdi_config[i]
        if 'description' in names:
            bdi_desc.append((names['name']))
        else:
            bdi_desc.append(None)

    # * LoopBack
    loopback_config = record_list[configuration][cisco]['interface']['Loopback']
    loopback_name = [x['name'] for x in loopback_config]
    loopback_description = [x['description']
                            for x in loopback_config]

    # * Put together
    postgre_names = ten_gigabit_names + one_gigabit_names + port_channel_names

    postgre_desc = ten_gigabit_desription + \
        one_gigabit_desription + port_channel_desription

    postgre_config = ten_gigabit_config + one_gigabit_config + port_channel_config

    postgre_port_channel_id = ten_channel_group + \
        [None]*len(one_gigabit_names) + [None] * len(port_channel_names)

    postgre_mtu = ten_gigabit_mtu + one_gigabit_mtu + port_channel_mtu

    postgre_config_json = []
    for i in postgre_config:
        postgre_config_json.append(Json(i))


if __name__ == '__main__':
    create_table()
    for i in range(len(postgre_names)):
        insert_data([(postgre_names[i], postgre_desc[i],
                      postgre_config_json[i], postgre_port_channel_id[1], postgre_mtu[i]), ])
    print("OK")
