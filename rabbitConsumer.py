import rabbitpy

with rabbitpy.Connection('amqp://valkiria_user:314159265@mizar.kyiv.ua:5672/valkiria') as conn:
    with conn.channel() as channel:
        queue = rabbitpy.Queue(channel, 'frequency464')

        # Exit on CTRL-C
        try:
            # Consume the message
            for message in queue:
                frequency = message.body.decode("utf-8")
                if frequency != '':
                    print(f'frequency = {frequency}')
                else:
                    print('queue is emty')
                #message.pprint(True)
                message.ack()

        except KeyboardInterrupt:
            print('Exited consumer')