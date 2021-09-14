# aws-ec2-pricing

![Table of AWS EC2 prices in SQL](/docs/example-query.png)

Collect AWS EC2 prices from AWS API to SQL table to analyze them.

<a href="https://pypi.org/project/aws-ec2-pricing/"><img alt="PyPI" src="https://img.shields.io/pypi/v/aws-ec2-pricing?logo=pypi&color=blue"></a>

**Table of contents**:

* <a href="#usage">Usage</a>
  * <a href="#download">download</a>
  * <a href="#build">build</a>
* <a href="#installation">Installation</a>
* <a href="#working">Working with data</a>
  * <a href="#table">Table columns and meaning</a>
  * <a href="#queries">How to run queries</a>
* <a href="#limitations">Limitations</a>
* <a href="#future">Future plans</a>

<a id="usage"></a>

## Usage

Make sure AWS credentials are set as environment variables or are available otherwise to `boto3` library
which this program uses to connect to AWS API.

```shell
Usage: ec2pricing [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  build     Build SQLite database with prices from given JSON
  download  Download EC2 prices to JSON file
```

<a id="download"></a>
Download all "On Demand" prices for all regions for "Shared" instances into a JSON file.


```shell
ec2pricing download
```

<a id="build"></a>
Build a SQLite database from that JSON file.

*You can see an example of built database in `examples/prices.db` file in this repo.*

```shell
ec2pricing build
```

<a id="working"></a>

The resulting file is a SQLite database with a single `prices` table in it.

<a id="table"></a>
Resulting table `prices` in the `prices.db` file has following columns:

<table>
    <tr><th>Name</th><th>Description</th><th>Examples</th></tr>
    <tr><td><b>family</b></td><td>Instace family</td><td>General purpose, Compute optimized</td></tr>
    <tr><td><b>type</b></td><td>Instace type group</td><td>a1, t3a, c5</td></tr>
    <tr><td><b>size</b></td><td>Instace size</td><td>nano, micro, xlarge, 32xlarge</td></tr>
    <tr><td>burst</td><td>Is instance burstable?</td><td>Yes, No</td></tr>
    <tr><td>base</td><td>Baseline performance of CPU (%)</td><td>5, 10, 100</td></tr>
    <tr><td>processor</td><td>Name of the physical CPU</td><td>AWS Graviton, AMD EPYC</td></tr>
    <tr><td>bit</td><td>CPU bitness</td><td>32-bit, 64-bit</td></tr>
    <tr><td><b>arch</b></td><td>CPU architecture</td><td>arm, x86</td></tr>
    <tr><td>tenancy</td><td>Instance tenancy</td><td>Shared, Dedicated, Host</td></tr>
    <tr><td><b>region</b></td><td>AWS Region</td><td>US East (Ohio), EU (Ireland)</td></tr>
    <tr><td><b>vcpu</b></td><td>Number of virtual cores</td><td>1, 2, 32</td></tr>
    <tr><td><b>memory</b></td><td>Amount of RAM</td><td>0.5 GiB, 128 GiB</td></tr>
    <tr><td>storage</td><td>Storage type</td><td>EBS only, 1x60GB NVM</td></tr>
    <tr><td>os</td><td>Operating System</td><td>Linux</td></tr>
    <tr><td>norm</td><td>Normalization scale factor (used by AWS to compare instances)</td><td>0.5, 1.0, 8.0</td></tr>
    <tr><td>speed</td><td>Declared CPU clock speed</td><td>2.5 GHz, Up to 3.2 Ghz. 0 GHz</td></tr>
    <tr><td><b>actual</b></td><td>Actual CPU clock speed multiplied by baseline</td><td>0.125 GHz, 2.5 Ghz</td></tr>
    <tr><td>network</td><td>Network performance</td><td>Up to 3500 MiB</td></tr>
    <tr><td>gen</td><td>Is it current generation of instances?</td><td>Yes, No</td></tr>
    <tr><td>cur</td><td>Price currency</td><td>USD, CNY</td></tr>
    <tr><td><b>hourly</b></td><td>Hourly price</td><td>0.0255</td></tr>
    <tr><td><b>montly</b></td><td>Monthly price (hourly * 24 * 30)</td><td>3.844</td></tr>
    <tr><td>starting</td><td>Date from which Amazon offers this price</td><td>2021-09-01T00:00:00Z</td></tr>

</table>

<a id="queries"></a>
The built database can be opened in any SQL IDE, for example, DBeaver (open source SQL editor) or in any other way.
You can then run queries in it.

**Show cheapest x86-64 virtual machines**:

```sql
SELECT * FROM prices WHERE arch = 'x86'
 ORDER BY monthly;
```

**Show cheapest ARM machines in Ireland**:

```sql
SELECT * FROM prices
 WHERE arch = 'arm' AND region = "EU (Ireland)"
 ORDER BY monthly;
```

**Sort all machines alpabetically by their family, type and power**:

```sql
SELECT * FROM prices
 ORDER BY family, type, norm;
```

<a id="limitations"></a>

## Limitations

Currently, downloaded prices are limited to instances with:

* "Shared" tenancy
* "Linux" operating system
* Support for VPC networking
* Only "On Demand" pricing, no reserved instances or saving plans
* "Used" capacity reservation

All these are default settings for EC2 instances when you check prices for them on AWS pricng website.

<a id="installation"></a>

## Installation

This program is written in Python and can be installed via `pip`.

```shell
pip install aws-ec2-pricing
```

## Build it and run it yourself

### Set up via pip and virtual environemnt

* Create a virtual environment

  ```shell
  python3 -m venv .venv
  source ./.venv/bin/activate
  ```

* Install requirements into it

  ```shell
  pip install -r requirements.txt
  ```

* Run the program

  ```shell
  python3 ec2pricing/__init__.py download
  ```

### Set up via poetry

* Tell poetry which version of python available in your system to use

  ```shell
  poetry env use 3.9.7
  ```

* Install dependencies and create virtual environment

  ```shell
  poetry install
  ```

* Run program

  ```shell
  poetry run ec2pricing download
  ```

<a id="future"></a>

## Feature plans

* [ ] Static website that displays the table along with the filters
* [ ] Add search filters as key-value pairs for initial price download
* [ ] Search for instances other than shared or Linux based
* [ ] Support saving plans, reserved instances, free tier

## Copyright & License

* This program is distributed under Apache 2 License.
* All AWS and Amazon related trademarks or symbols are not mine.
* Prices obtained through this program are not an offer and should not be treated as official.
