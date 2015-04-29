import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]
        settings = dict(
            autoreload=True,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", messages=ChatSocketHandler.cache)

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    callbacks = set()
    cache = []
    cache_size = 200

    def get_compression_options(self):
        # Non-None enables compression with default options.
        logging.info("get_compression_options")
        return {}

    def open(self):
        logging.info("open")
        ChatSocketHandler.callbacks.add(self)

    def on_close(self):
        logging.info("on_close")
        ChatSocketHandler.callbacks.remove(self)

    def on_message(self, message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
            }
        chat["html"] = tornado.escape.to_basestring(self.render_string("message.html", message=chat))

        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)

    @classmethod
    def update_cache(cls, chat):
        logging.info("update_cache")
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[cls.cache_size:]

    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message to %d callbacks", len(cls.callbacks))
        for callback in cls.callbacks:
            try:
                logging.info("send_update")
                callback.write_message(chat)
                logging.info("sent_update")
            except:
                logging.error("Error sending message", exc_info=True)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()