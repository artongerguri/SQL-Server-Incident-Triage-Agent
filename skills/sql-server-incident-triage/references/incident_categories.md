# SQL Server Incident Categories

Use these categories as a triage reference. Keep checks read-only and require
DBA approval before operational actions.

## Backup / Storage

Signals:

- backup failed
- operating system error 112
- not enough disk space
- insufficient disk space

First checks:

- backup destination free space
- SQL Agent job history
- SQL Server error log
- database recovery model and log reuse status

Avoid:

- deleting backups without retention review
- assuming shrink fixes the incident

## Transaction Log

Signals:

- transaction log is full
- `log_reuse_wait_desc = ACTIVE_TRANSACTION`
- DBCC OPENTRAN
- oldest active transaction

First checks:

- DBCC OPENTRAN
- `sys.databases.log_reuse_wait_desc`
- active requests and sessions
- transaction log space usage

Avoid:

- shrinking before log reuse is understood
- killing sessions without rollback risk review

## Transaction Log Growth

Signals:

- frequent log autogrowth
- VLF pressure
- WRITELOG waits
- log write latency

First checks:

- DBCC SQLPERF(LOGSPACE)
- SQL Server error log for autogrowth messages
- WRITELOG waits
- log backup cadence

Avoid:

- repeated shrink/regrow cycles
- percentage-based tiny growth settings

## TempDB

Signals:

- error 1105
- could not allocate space in tempdb
- version store growth
- TempDB is full

First checks:

- TempDB file sizes and growth settings
- session/task space usage
- version store usage
- large reporting or ETL workloads

Avoid:

- restarting before identifying the workload
- adding space without checking the underlying pressure

## Blocking / Locks

Signals:

- blocking_session_id
- LCK_M waits
- head blocker
- blocked process report

First checks:

- active requests
- lock waits
- head blocker session metadata
- related import/report/job activity

Avoid:

- killing sessions before confirming business impact and rollback risk

## Concurrency / Deadlock

Signals:

- error 1205
- deadlock victim
- deadlock graph

First checks:

- system_health deadlock graph
- involved tables and indexes
- transaction scope
- lock order

Avoid:

- treating deadlocks as only infrastructure problems

## Database Integrity

Signals:

- suspect database
- recovery pending
- error 823, 824, or 825
- page checksum
- suspect_pages

First checks:

- database state
- SQL Server error log
- msdb suspect_pages
- DBCC CHECKDB in a controlled context or restored copy
- backup availability

Avoid:

- repair_allow_data_loss as first response
- changing database state without preserving evidence

## Authentication / Access

Signals:

- login failed
- error 18456
- SSPI handshake failed
- cannot open database requested by login

First checks:

- SQL Server error log and 18456 state
- login disabled/default database
- database online/access state
- affected application/user scope

Avoid:

- resetting credentials before identifying the failure state

## High Availability

Signals:

- Always On
- availability group not synchronizing
- replica disconnected
- log send queue
- redo queue
- synchronization health

First checks:

- replica role and connected state
- database synchronization state
- queue sizes
- listener/network/cluster health

Avoid:

- force failover before checking data loss risk and quorum

## Replication

Signals:

- replication
- publication/subscription
- distribution agent
- log reader agent
- linked server

First checks:

- Replication Monitor
- SQL Agent replication jobs
- publisher/distributor/subscriber connectivity
- article and schema object names

Avoid:

- dropping/recreating replication before isolating the failing component

## Performance / Query Store

Signals:

- high CPU
- Query Store
- slow query
- regressed query
- logical reads

First checks:

- Query Store top resource consumers
- recent deployments
- execution plan changes
- missing/outdated statistics

Avoid:

- forcing plans or adding indexes without plan review

## Memory Pressure

Signals:

- RESOURCE_SEMAPHORE
- error 701 or 802
- out of memory
- large memory grants

First checks:

- memory-related waits
- memory clerks
- query memory grants
- OS and SQL Server memory configuration

Avoid:

- changing max server memory during incident without checking OS pressure

## Connectivity

Signals:

- timeout expired
- pre-login handshake timeout
- transport-level error
- connection pool exhaustion
- forcibly closed connection

First checks:

- error log network/login messages
- active sessions and connections
- affected client scope
- DNS/listener/firewall changes

Avoid:

- assuming SQL Server engine is the root cause before checking network and app layers

