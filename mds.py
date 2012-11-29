import redis, logging, random
import messages_pb2 as msg
import rpc, transientdb

def guidAssign(x, y):
    x.a=y.a; x.b=y.b; x.c=y.c; x.d=y.d

def isGuidZero(x):
    return (x.a==0 and x.b==0 and x.c==0 and x.d==0)

def guid2Str(x):
    return "%08x-%08x-%08x-%08x" % (x.a, x.b, x.c, x.d)

def guidFromStr(s):
    ret=msg.Guid()
    s=s.split('-')
    ret.a=int(s[0], 16)
    ret.b=int(s[1], 16)
    ret.c=int(s[2], 16)
    ret.d=int(s[3], 16)
    return ret

class Object:
    def __init__(self, d=None):
        if isinstance(d, dict):
            self.__dict__=d

def message2object(message):
    "receive a PB message, returns its guid and a object describing the message"
    fields=message.ListFields()
    rst=Object()
    for f in fields:
        name=f[0].name
        value=f[1]
        if isinstance(value, msg.Guid):
            value=guid2Str(value)
        else:
            listable=getattr(value, 'ListFields', None)
            if listable:
                value=message2object(value, '')
            else:
                container=getattr(value, '_values', None)
                if container:
                    value=[message2object(x) for x in container]
        setattr(rst, name, value)
    return rst


class MDS:
    tdb=None
    stub=None
    def __init__(self, stub, transientdb):
        self.stub=stub
        self.tdb=transientdb
    def ChunkServerInfo(self, arg):
        logging.debug(type(arg))
        cksinfo=message2object(arg)
        self.tdb.putChunkServer(cksinfo)
    def NewChunk(self, arg):
        logging.debug(type(arg))
        if isGuidZero(arg.location):
            servers=self.tdb.getChunkServers()
            x=random.choice(servers)
            x=guidFromStr(x)
            guidAssign(arg.location, x)
        logging.debug("NewChunk on chunk server %s", arg.location)
        retv=self.stub.callMethod_on("NewChunk", arg, arg.location)
        return retv
    
    @staticmethod    
    def splitLocations(pairs):
        "input should be like [(guid, location), (guid, location), ...], where locations are ordered"
        guids=None; location=None;
        for p in pairs:
            if location==None:
                guids=[p[0],]
                location=p[1]
                continue
            elif location==p[1]:
                guids.append(p[0])
            elif location!=p[1]:
                yield guids, location
                guids=[p[0], ]
                location=p[1]
        yield guids, location

    def DeleteChunk(self, arg):
        logging.debug(type(arg))
        chunks=self.tdb.getChunks(arg.guids)
        pairs=[ (c.guid, c.serverid) for c in chunks ]
        pairs.sort(key = lambda x : x[1])
        done=[]; ret=None;
        for guids,location in MDS.splitLocations(pairs):
            arg.guids=guids
            ret=self.stub.callMethod_on("DeleteChunk", arg, location)
            done=done+ret.guids
            if ret.error:
                break;
        ret.guids=done
        return ret

    def NewVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.NewVolume_Response()
        return ret

    def AssembleVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.AssembleVolume_Response()
        ret.access_point='no access_point'
        return ret
    def DisassembleVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.DisassembleVolume_Response()
        ret.access_point=arg.access_point
        return ret
    def RepairVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.RepairVolume_Response()
        return ret
    def ReadVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.ReadVolume_Response()
        ret.volume.size=0
        return ret
    def WriteVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.WriteVolume_Response()
        return ret
    def MoveVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.MoveVolume_Response()
        return ret
    def ChMod(self, arg):
        logging.debug(type(arg))
        ret=msg.ChMod_Response()
        return ret
    def DeleteVolume(self, arg):
        logging.debug(type(arg))
        ret=msg.DeleteVolume_Response()
        return ret
    def CreateLink(self, arg):
        logging.debug(type(arg))
        ret=msg.CreateLink_Response()
        return ret


def test_main():
    logging.basicConfig(level=logging.DEBUG)
    sched=rpc.Scheduler()
    stub=rpc.RpcStubCo(msg.Guid(), sched, MDS)
    tdb=transientdb.TransientDB()
    server=MDS(stub, tdb)
    service=rpc.RpcServiceCo(sched, server)
    stub.setServiceCo(service)
    while True:
        service.listen()
        print "let's listen again"

if __name__=="__main__":
    test_main()
