import inspect
try:
    import Queue
except:
    import queue as Queue
import sys
import threading
import traceback

class GitAnnexESRP(threading.Thread):

  class Cost:
    CHEAP = 100
    NEARLY_CHEAP = 110
    SEMI_EXPENSIVE = 175
    EXPENSIVE = 200
    VERY_EXPENSIVE = 1000
    ADD_ENCRYPTED = 50

  def __init__(self, mockinput = None):
    self.stdin = mockinput if mockinput else sys.stdin
    try:
      threading.Thread.__init__(self)
      self.send_lock = threading.RLock()
      self.replies_queue = Queue.Queue()
      self.handling_queue = Queue.Queue()
      self.incomingError = None
      self.start()
      self.VERSION(1)
      while self.is_alive() or not self.handling_queue.empty():
        try:
          command, args = self.handling_queue.get(True, 1)
        except Queue.Empty:
          continue
        try:
          handler = getattr(self, 'on' + command)
          if args != None:
            argspec = inspect.getargspec(handler)
            if argspec[1] != None:
              nArgs = -1
            else:
              nArgs = len(argspec[0]) - 1
            handler(*(args.split(' ', nArgs)))
          else:
            handler()
        except (AttributeError, NotImplementedError):
          self.UNSUPPORTED_REQUEST()
    except Exception:
      self.exception()
    self.finish()

  class MessageReply:
    def __init__(self, **replies):
      self.event = threading.Event()
      self.accepted = replies
      self.repeatUntilEmpty = False
      self.response = []
      self.error = False

    def setRepeatUntilEmpty(self, value = True):
      self.repeatUntilEmpty = value

    def matches(self, command):
      return command in self.accepted

    # no response available
    def fail(self, message):
      self.error = True
      self.errorMessage = message
      self.event.set()

    # returns True iff reply has been fully filled
    def process(self, command, args):
      if not (self.repeatUntilEmpty and args == ''):
        self.response[len(self.response):] = args.split(' ', self.accepted[command])

      if not (self.repeatUntilEmpty and args != ''):
        self.event.set()
        return True
      return False

  # receive lines and process them
  def run(self):
    reply = None
    while True:
      try:
        line = self.stdin.readline()
        if line == "":
          break
        # funny tricks here make sure args = None if no args are provided
        line = line[:-1].split(' ',1) + [None]
        command, args = line[:2]

        # see if anybody was waiting for this command
        if reply == None:
          try:
            reply = self.replies_queue.get_nowait()
          except Queue.Empty:
            pass
        if reply != None and reply.matches(command):
          if reply.process(command, args):
            reply = None
          continue

        # nobody was waiting, pass it to handler
        self.handling_queue.put((command, args))
        self.running = False

      except Exception:
        self.exception()
        break

    if self.incomingError == None:
      self.incomingError = "Connection closed"

    while not self.replies_queue.empty():
      self.replies_queue.get().fail(self.incomingError)



  # send a message without waiting for a reply
  def send(self, *args):
    with self.send_lock:
      sys.stdout.write(" ".join(map(str,args)))
      sys.stdout.write("\n")
      sys.stdout.flush()

  # send a message and block on a reply
  # **replies is in format of COMMAND=argcount
  def getReply(self, reply, *args):
    with self.send_lock:
      self.replies_queue.put(reply)
      self.send(*args)
    reply.event.wait()
    if reply.error:
      raise Exception(reply.errorMessage)
    return reply.response

  # send a message and return a VALUE reply
  def getValue(self, *args):
    return self.getReply(GitAnnexESRP.MessageReply(VALUE=1), *args)[0]

  # handshake
  def VERSION(self, version):
    self.send("VERSION", version)

  # update how many bytes have been transferred, granularity 1%
  def PROGRESS(self, bytes):
    self.send("PROGRESS", bytes)

  # get two-level hash path for <key> as used in hash directory
  def DIRHASH(self, key):
    return self.getValue('DIRHASH', key)

  # normally sent during initremote, sets config value
  def SETCONFIG(self, setting, value):
    self.send('SETCONFIG', setting, value)

  # get configuration value, can be set by user
  def GETCONFIG(self, setting):
    return self.getValue('GETCONFIG', setting)

  # usually during initremote, stores secure credentials
  # may be included in repository if embedcreds config is set to yes
  def SETCREDS(self, setting, user, password):
    self.send('SETCREDS', setting, user, password)

  # git-annex replies CREDS <user> <password>
  def GETCREDS(self, setting):
    return self.getReply(GitAnnexESRP.MessageReply(CREDS=2), 'GETCREDS', setting)

  # git-annex replies VALUE <uuid>
  def GETUUID(self):
    return self.getValue('GETUUID')

  # git-annex replies VALUE <git directory of repository>
  def GETGITDIR(self):
    return self.getValue('GETGITDIR')

  # set preferred content
  def SETWANTED(self, preferred_content):
    self.send('SETWANTED', preferred_content)

  # get preferred content expression as VALUE
  def GETWANTED(self):
    return self.getValue('GETWANTED')

  # can store a persistent state for a key (perhaps useful name mapping)
  def SETSTATE(self, key, value):
    self.send('SETSTATE', key, value)

  # gets VALUE for setstate
  def GETSTATE(self, key):
    return self.getValue('GETSTATE', key)
    
  # records a URL where <key> may be downlaoded
  # if public urls are available, esrp should document that it can be
  # used in readonly mode, allowing retrieval of files when not installed
  def SETURLPRESENT(self, key, url):
    self.send('SETURLPRESENT', key, url)

  # records that key may not longer be downloaded from specified URL
  def SETURLMISSING(self, key, url):
    self.send('SETURLMISSING', key, url)

  # records an URI where <key> may be downloaded from; something the
  # CLAIMURL handler will claim
  def SETURIPRESENT(self, key, uri):
    self.send('SETURIPRESENT', key, uri)

  # records that key is no longer available at uri
  def SETURIMISSING(self, key, uri):
    self.send('SETURIMISSING', key, uri)

  # gets urls for <key> which start with <prefix>
  # reply is a sequence of VALUEs, the final one empty
  def GETURLS(self, key, prefix=""):
    reply = GitAnnexESRP.MessageReply(VALUE=1)
    reply.setRepeatUntilEmpty()
    return self.getReply(reply, 'GETURLS', key, prefix)

  # not actually a git-annex command
  # returns the size of the content of the key
  def GETSIZE(self, key):
    keymetadata = key.split('--')[0]
    if keymetadata.find('-s') != -1:
      filesize = int(keymetadata.split('-s')[1].split('-')[0])
    else:
      filesize = None
    if keymetadata.find('-S') != -1:
      chunksize = int(keymetadata.split('-S')[1].split('-')[0])
    else:
      chunksize = None
    if filesize is None:
      filesize = chunksize
    elif chunksize is not None:
      if chunksize > filesize:
        temp = chunksize
        chunksize = filesize
        filesize = temp
      chunk = int(keymetadata.split('-C')[1].split('-')[0])
      if chunk * chunksize > filesize:
        filesize = filesize % chunksize
      else:
        filesize = chunksize
    self.DEBUG('calculated keysize of ' + str(filesize) + ' from ' + key)
    return filesize

  # output <message> if --debug is enabled
  def DEBUG(self, message):
    self.send('DEBUG', message)

  # end connection with failure
  def ERROR(self, message):
    self.send('ERROR', message)

  # report exception
  def exception(self, error = True):
    for line in traceback.format_exc().split("\n"):
      self.DEBUG(line)
    line = traceback.extract_tb(sys.exc_info()[2])[-1]
    mesg = "%s:%d %s %s" % (line[0],
                            line[1],
                            sys.exc_info()[0].__name__,
                            repr(sys.exc_info()[1]))
    self.incomingError = mesg
    if error:
      self.ERROR(mesg)
    else:
      sys.stderr.write(mesg + "\n")

  # booted up, give me instructions
  # git-annex will indicate shutdown by closing stdin
  def PREPARE_SUCCESS(self):
    self.send('PREPARE-SUCCESS')

  # special remote cannot be prepared(self, message):
  def PREPARE_FAILURE(self, message):
    self.send('PREPARE-FAILURE', message)

  # esrp does not know how to handle request
  def UNSUPPORTED_REQUEST(self):
    self.send('UNSUPPORTED-REQUEST')

  # SERVER commands

  # create the remote, may be called more than once
  # reply INITREMOTE-SUCCESS or INITREMOTE-FAILURE <message>
  def onINITREMOTE(self):
    try:
      self.initRemote()
    except Exception as e:
      self.exception(False)
      return self.send('INITREMOTE-FAILURE', e.message)
    return self.send('INITREMOTE-SUCCESS')

  # special remote shall boot up, may now send commands
  # expected to ask for configuration, then reply
  # with PREPARE-SUCCESS or PREPARE-FAILURE <message>
  def onPREPARE(self):
    try:
      self.prepare()
    except Exception as e:
      self.exception(False)
      return self.send('PREPARE-FAILURE', e.message)
    return self.send('PREPARE-SUCCESS')

  # store/retrieve a key, commands may be sent during transfer
  # reply with TRANSFER-SUCCESS|FAILURE STORE|RETRIEVE <key> [message]
  def onTRANSFER(self, type, key, file):
    try:
      if type == "STORE":
        self.store(key, file)
      elif type == "RETRIEVE":
        self.retrieve(key, file)
      else:
        return self.UNSUPPORTED_REQUEST()
    except Exception as e:
      self.exception(False)
      return self.send('TRANSFER-FAILURE', type, key, e.message)
    return self.send('TRANSFER-SUCCESS', type, key)

  # request to check if key is present
  # reply CHECKPRESENT-SUCCESS <key>, CHECKPRESENT-FAILURE <key>,
  # or CHECKPRESENT-UNKNOWN <key> <message>
  def onCHECKPRESENT(self, key):
    try:
      if self.isPresent(key):
        return self.send('CHECKPRESENT-SUCCESS', key)
      else:
        return self.send('CHECKPRESENT-FAILURE', key)
    except Exception as e:
      self.exception(False)
      return self.send('CHECKPRESENT-UNKNOWN', key, e.message)

  # request to remove a key's contents
  # reply REMOVE-SUCCESS <key> or REMOVE-FAILURE <key> <message>
  def onREMOVE(self, key):
    try:
      self.remove(key)
    except Exception as e:
      self.exception(False)
      return self.send('REMOVE-FAILURE', key, e.message)
    return self.send('REMOVE-SUCCESS', key)

  #  -- end of required responses

  # requests to return a use cost, see Config/Cost.hs
  # reply COST <int>
  def onGETCOST(self):
    return self.send('COST', self.getCost())

  # implement if remote is only locally reachable
  # reply AVAILABILITY GLOBAL|LOCAL
  def onGETAVAILABILITY(self):
    if self.isLocal():
      return self.send('AVAILABILITY', 'LOCAL')
    else:
      return self.send('AVAILABILITY', 'GLOBAL')
       
  # ask if remote wishes to claim responsibility for downloading url
  # reply CLAIMURL-SUCCESS or CLAIMURL-FAILURE
  def onCLAIMURL(self, url):
    if self.claimsUrl(url):
      return self.send('CLAIMURL-SUCCESS')
    else:
      return self.send('CLAIMURL-FAILURE')

  # check if url's content can currently be downloaded
  # reply CHECKURL-FAILURE, CHECKURL-CONTENTS <size>|UNKNOWN [filename],
  # or CHECKURL-MULTI <url> <size>|UNKNOWN <filename> ...
  # which is used if multiple files with urls are contained
  def onCHECKURL(self, url):
    files = self.checkUrl(url)
    if files == None or len(files) == 0:
      return self.send('CHECKURL-FAILURE')
    for file in files:
      if file[1] == None:
        file[1] = 'UNKNOWN'
    if len(files) == 1 and (files[0][0] == None or files[0][0] == "" or files[0][0] == url):
      return self.send('CHECKURL-CONTENTS', files[0][1], files[0][2])
    return self.send('CHECKURL-MULTI', *[item for file in files for item in file])
    
  # provide information about ways to access content of key
  # reply WHEREIS-SUCCESS <url/location> or WHEREIS-FAILURE
  # not needed if SETURIPRESENT is used
  def onWHEREIS(self, key):
    location = self.whereIs(key)
    if location == None:
      return self.send('WHEREIS-FAILURE')
    return self.send('WHEREIS-SUCCESS', location)

  # things got too messed up to continue, esrp may exit with its own ERROR
  def onERROR(self, message):
    self.incomingError = message;
    return self.error(message)

  #################################################
  # Methods expected to be overridden.
  # Handlers for server commands.

  # create new special remote, may be called repeatedly on the same remote,
  # or not at all if the remote has already been configured
  # usually uses SETCONFIG, SETCREDS
  def initRemote(self):
    pass

  # activate remote, called once at start
  # query configuration with GETCONFIG, GETCREDS
  def prepare(self):
    pass

  # connection closed, deactivate remote if activated
  def finish(self):
    pass

  # store file in key
  def store(self, key, file):
    raise NotImplementedError("store not implemented")

  # retrieve key to file
  def retrieve(self, key, file):
    raise NotImplementedError("retrieve not implemented")

  # return False or True if key is present
  def isPresent(self, key):
    raise NotImplementedError("isPresent not implemented")

  # remove a key's contents
  def remove(self, key):
    raise NotImplementedError("remove not implemented")

  ### Optional:
  # get use cost
  def getCost(self):
    raise NotImplementedError()

  # override to return True for local remotes
  def isLocal(self):
    raise NotImplementedError()

  # return True if responsible for downloading passed url
  def claimsUrl(self, url):
    raise NotImplementedError()

  # return a list of (url, size, filename) that may currently be
  # downloaded from the provided url
  # size may be None if unknown
  # return empty list if cannot currently download url
  def checkUrl(self, url):
    raise NotImplementedError()

  # return a location (such as url) of key to show user
  # may return None
  def whereIs(self, key):
    raise NotImplementedError()

  # actions to perform when git-annex indicates an error
  def error(self, message):
    # sends error back to server, where hopefully it will be displayed,
    # and closes the connection
    self.ERROR(message)
