"""Small synthetic process used only by the disposable Gate738P crash test."""

from __future__ import annotations

import asyncio
import os

import asyncpg
from sqlalchemy import text


async def hold_transaction() -> None:
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await connection.execute("BEGIN")
        result = await connection.execute(
            "UPDATE public.users SET username=$1 WHERE id=$2",
            os.environ["GATE738P_WRITE_VALUE"],
            int(os.environ["GATE738P_USER_ID"]),
        )
        if result != "UPDATE 1":
            raise RuntimeError("synthetic OLD row was not updated")
        print("TX_READY", flush=True)
        await asyncio.Event().wait()
    finally:
        await connection.close()


async def expect_old_write_denied() -> None:
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await connection.execute("BEGIN")
        try:
            await connection.execute(
                "UPDATE public.users SET username=$1 WHERE id=$2",
                os.environ["GATE738P_WRITE_VALUE"],
                int(os.environ["GATE738P_USER_ID"]),
            )
        except asyncpg.PostgresError:
            await connection.execute("ROLLBACK")
            print("OLD_WRITE_DENIED", flush=True)
            return
        await connection.execute("ROLLBACK")
        raise RuntimeError("fenced OLD login unexpectedly wrote")
    finally:
        await connection.close()


async def candidate_application_write() -> None:
    from app.db.base import build_session_factory

    factory = build_session_factory(
        os.environ["DATABASE_URL"],
        True,
        os.environ["WRITER_GENERATION"],
        os.environ["WRITER_INSTANCE_ID"],
        os.environ["WRITER_DATABASE_ROLE"],
    )
    async with factory() as session, session.begin():
        result = await session.execute(
            text("UPDATE public.users SET username=:value WHERE id=:user_id"),
            {"value": os.environ["GATE738P_WRITE_VALUE"], "user_id": int(os.environ["GATE738P_USER_ID"])},
        )
        if result.rowcount != 1:
            raise RuntimeError("candidate synthetic row update did not affect exactly one row")
    print("CANDIDATE_WRITE_COMMITTED", flush=True)


async def main() -> None:
    mode = os.environ.get("GATE738P_CRASH_MODE", "")
    print(f"GATE738P_CRASH_WRITER_START:{mode}", flush=True)
    if mode == "hold":
        await hold_transaction()
    elif mode == "old-write":
        await expect_old_write_denied()
    elif mode == "candidate-write":
        await candidate_application_write()
    else:
        raise RuntimeError("unsupported disposable crash-test mode")


if __name__ == "__main__":
    asyncio.run(main())
