# Copyright 2021 Vagiz Duseev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
from pprint import pprint
import re
import sqlite3
from typing import Any, List, Optional

import boto3
import click


from .version import __version__


EC2NAME = "AmazonEC2"
FORMATVER = "aws_v1"
SQL_DROP_TABLE = """
DROP TABLE IF EXISTS prices
"""
SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS prices (
    family TEXT,
    type TEXT,
    size TEXT,
    burst TEXT,
    base REAL,
    processor TEXT,
    bit TEXT,
    arch TEXT,
    tenancy TEXT,
    region TEXT,
    vcpu INT,
    memory REAL,
    storage TEXT,
    os TEXT,
    norm REAL,
    speed TEXT,
    actual TEXT,
    network TEXT,
    gen TEXT,
    cur TEXT,
    hourly REAL,
    monthly REAL,
    starting TEXT
)
"""
SQL_INSERT = """
INSERT INTO prices (
    family,
    type,
    size,
    burst,
    base,
    processor,
    bit,
    arch,
    tenancy,
    region,
    vcpu,
    memory,
    storage,
    os,
    norm,
    speed,
    actual,
    network,
    gen,
    cur,
    hourly,
    monthly,
    starting
) VALUES (
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?
)
"""
SPEED_PATTERN = r"^[^\d+]*(\d+(\.\d+)?)[^\d+]+$"


# Singleton
_client = None
_dbcon = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
def main():
    pass


@main.command(short_help="Build SQLite database with prices from given JSON")
@click.option("-j", "--json", "path", default="prices.json", type=click.Path(dir_okay=False, exists=True), help="Path to json file from which prices will be read")
@click.option("-d", "--db", default="prices.db", type=click.Path(dir_okay=False), help="Path to SQLite DB file in which table will be built")
def build(path, db):
    initialize_database(db)

    ec2_prices = {}
    with open(path, "r") as f:
        dump = f.read()
        ec2_prices = json.loads(dump)

    to_insert = []
    for i in ec2_prices:
        a = i["product"]["attributes"]
        t = i["terms"]["OnDemand"]

        # Read attributes
        family = a["instanceFamily"]
        memory = a["memory"]
        region = a["location"]
        vcpu = a["vcpu"]
        storage = a["storage"]
        os = a["operatingSystem"]
        processor = a["physicalProcessor"]
        network = a["networkPerformance"]
        _parts = a["instanceType"].split(".")
        _type = _parts[0]
        size = "".join(_parts[1:]) if len(_parts) > 1 else ""
        tenancy = a["tenancy"]
        norm = a["normalizationSizeFactor"]
        gen = a["currentGeneration"]
        bit = a["processorArchitecture"]
        arch = "arm" if "Graviton" in processor else "x86"
        burstable = "Yes" if "t" in _type else "No"
        if burstable == "No":
            base = 100.0
        else:
            base = 10.0
            if size == "nano":
                base = 5.0
            elif size == "micro":
                base = 10.0
            elif size == "small":
                base = 20.0
            elif size == "medium":
                base = 40.0
            elif size == "large":
                base = 60.0
            elif size == "xlarge":
                base = 90.0
            elif size == "2xlarge":
                base = 135.0

        speed = a.get("clockSpeed", "0 GHz")
        _speed = re.search(SPEED_PATTERN, speed).group(1)
        _speed = float(_speed)
        actual = f"{_speed * base / 100} GHz"

        _deal = list(t.values())[0]
        starting = _deal["effectiveDate"]
        _dimension = list(_deal["priceDimensions"].values())[0]

        unit = _dimension["unit"]
        cur = list(_dimension["pricePerUnit"].keys())[0]
        price = _dimension["pricePerUnit"][cur]
        price = float(price)
        hourly = price if unit == "Hrs" else 0.0
        monthly = hourly * 24 * 30

        to_insert.append((
            family,
            _type,
            size,
            burstable,
            base,
            processor,
            bit,
            arch,
            tenancy,
            region,
            vcpu,
            memory,
            storage,
            os,
            norm,
            speed,
            actual,
            network,
            gen,
            cur,
            hourly,
            monthly,
            starting
        ))

    logger.info(f"Extracted {len(to_insert)} rows to insert")

    con = dbcon(db)
    cur = con.cursor()
    cur.executemany(
        SQL_INSERT,
        to_insert
    )

    con.commit()
    logger.info(f"Successfully inserted {len(to_insert)} rows to database")
    con.close()


@main.command(short_help="Download EC2 prices to JSON file")
@click.option("-j", "--json", "path", default="prices.json", type=click.Path(dir_okay=False), help="Path to json file into which prices will be downloaded")
def download(path):

    # ec2_attrs = get_all_attributes(service_code=EC2NAME)
    # pprint(ec2_attrs)

    # ec2_values = get_all_attribute_values("instanceType", service_code=EC2NAME)
    # pprint(ec2_values)

    ec2_prices = get_all_products(
        service_code=EC2NAME,
        # instanceFamily="General purpose",
        # location="US East (Ohio)",
        operatingSystem="Linux",
        vpcnetworkingsupport="true",
        # processorArchitecture="64-bit",
        marketoption="OnDemand",
        tenancy="Shared",
        capacitystatus="Used",
    )

    logger.info(f"In total {len(ec2_prices)} prices have been downloaded")

    dump = json.dumps(ec2_prices, indent=2)
    with open(path, "w") as f:
        f.write(dump)

    logger.info(f"Successfully saved downloaded prices to {path}")


def get_all_attribute_values(attribute_name: str, service_code: str = EC2NAME) -> List[Any]:
    c = pricing()

    values = []

    next_token: Optional[str] = None
    continue_reading: bool = True
    while continue_reading:

        kwargs = {"ServiceCode": service_code, "AttributeName": attribute_name}
        if next_token:
            kwargs["NextToken"] = next_token

        resp = c.get_attribute_values(**kwargs)

        obtained_values = [a["Value"] for a in resp["AttributeValues"]]
        next_token = resp.get("NextToken", None)

        values.extend(obtained_values)
        continue_reading = next_token is not None

    return values


def get_all_products(service_code: str = EC2NAME, **kwargs) -> List[Any]:
    c = pricing()

    values = []

    next_token: Optional[str] = None
    continue_reading: bool = True
    while continue_reading:

        req_kwargs = {
            "ServiceCode": service_code,
            "FormatVersion": FORMATVER,
            "Filters": [
                {
                    "Type": "TERM_MATCH",
                    "Field": k,
                    "Value": str(v),
                } for k, v in kwargs.items()
            ],
        }
        if next_token:
            req_kwargs["NextToken"] = next_token

        resp = c.get_products(**req_kwargs)

        obtained_values = [
            json.loads(v) for v in resp["PriceList"]
            #v for v in resp["PriceList"]
        ]
        next_token = resp.get("NextToken", None)

        logger.info(f"Size of pricing values array: {len(values)}")
        values.extend(obtained_values)
        continue_reading = next_token is not None

    return values


def get_all_attributes(service_code: str = EC2NAME):
    c = pricing()

    resp = c.describe_services(
        ServiceCode=service_code,
        FormatVersion=FORMATVER,
    )

    attrs = resp["Services"][0]["AttributeNames"]
    return attrs


def initialize_database(path):
    con = dbcon(path)
    cur = con.cursor()
    cur.execute(SQL_DROP_TABLE)
    cur.execute(SQL_CREATE_TABLE)
    con.commit()
    con.close()


def pricing():
    global _client

    if not _client:
        _client = boto3.client("pricing")
    return _client


def dbcon(path):
    global _dbcon

    _dbcon = sqlite3.connect(path)
    return _dbcon
