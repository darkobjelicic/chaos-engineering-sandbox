import asyncio
import json
import aio_pika

async def test():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
    channel = await connection.channel()
    
    exchange = await channel.declare_exchange('orders.events', aio_pika.ExchangeType.FANOUT, durable=True)
    queue = await channel.declare_queue('test.orders', durable=True)
    await queue.bind(exchange)
    
    print("Waiting for messages...")
    async with queue.iterator() as it:
        async for message in it:
            print(f"GOT: {message.body.decode()}")
            await message.ack()

asyncio.run(test())
