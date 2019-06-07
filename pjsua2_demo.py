import pjsua2 as pj
import subprocess
import multiprocessing as mp

#import time
# Subclass to extend the Account and get notifications etc.
#from concurrent.futures import ProcessPoolExecutor

# Call class
class Call(pj.Call):
    
    """
    High level Python Call object, derived from pjsua2's Call object.
    """
    
    def __init__(self, acc, peer_uri='', chat=None, call_id = pj.PJSUA_INVALID_ID):
        pj.Call.__init__(self, acc, call_id)
        self.acc = acc
        self.onhold = False
        self.am=None
        self.recorder=None
        self.connected=False
        self.canConnectPlayer=False
        self.callerPIDofparec=None
        self.fullRecordPIDofparec=None
        
    def onCallState(self, prm):
        ci = self.getInfo()
        connected = ci.state == pj.PJSIP_INV_STATE_CONFIRMED
        if(connected==True):
            cmd="/usr/bin/parec -d FullRecorder.monitor | /usr/bin/lame -r -V0 - /PJSUA2/example/outFullRecorder.mp3";
            subprocess.call("rm /PJSUA2/example/out*.wav".split())
            cmd="/usr/bin/ffmpeg -y -f pulse -i FullRecorder.monitor /PJSUA2/example/outFullRecorder.wav "
            self.fullRecordPIDofparec = subprocess.Popen(cmd.split())
            cmd="/usr/bin/parec -d CallerVoice.monitor | /usr/bin/lame -r -V0 - /PJSUA2/example/outCallerVoice.mp3";
            cmd="/usr/bin/ffmpeg -y -f pulse -i CallerVoice.monitor /PJSUA2/example/outCallerVoice.wav "
            self.callerPIDofparec  =  subprocess.Popen(cmd.split())

            self.connected=True
            print("########################################## Call connected")
            
            
            
        if(ci.state==pj.PJSIP_INV_STATE_DISCONNECTED):
            self.connected=False
            self.am=None
            self.canConnectPlayer=False

            self.onhold = False
            self.am=None
            self.recorder=None
            self.connected=False
            self.canConnectPlayer=False
                
            self.acc.c=None
            self.acc.acceptCall=False;
            self.acc.inCall=False;
            self.acc.call_id=None
            try:
                self.fullRecordPIDofparec.kill();
                self.callerPIDofparec.kill();
            except:
                pass
            print(">>>>>>>>>>>>>>>>>>>>>>> Call disconnected")



    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and \
              (mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE or \
               mi.status == pj.PJSUA_CALL_MEDIA_REMOTE_HOLD):
              
                m = self.getMedia(mi.index)
                am = pj.AudioMedia.typecastFromMedia(m)
                # connect ports
                #ep.audDevManager().getCaptureDevMedia().startTransmit(am)
                
                #ep.audDevManager().setPlaybackDev(self.acc.callerVoiceRecorderDeviceID);
                #amr = pj.AudioMediaRecorder.typecastFromAudioMedia(ep.audDevManager().getPlaybackDevMedia())
                #am.startTransmit(self.acc.amr)
               
                ep.audDevManager().setPlaybackDev(self.acc.fullRecorderDeviceID);
                am.startTransmit(ep.audDevManager().getPlaybackDevMedia())
                am.startTransmit(self.acc.amr)


                self.am=am
                self.canConnectPlayer=True

                if mi.status == pj.PJSUA_CALL_MEDIA_REMOTE_HOLD and not self.onhold:
                    #self.chat.addMessage(None, "'%s' sets call onhold" % (self.peerUri))
                    self.onhold = True
                elif mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE and self.onhold:
                    #self.chat.addMessage(None, "'%s' sets call active" % (self.peerUri))
                    self.onhold = False
        #raise Exception('onCallMediaState done!')        
                    
class Account(pj.Account):

    def __init__(self, ep=None):
        pj.Account.__init__(self)
        self.ep=ep
        self.c=None
        self.acceptCall=False;
        self.inCall=False;
        self.call_id=None
        self.callerVoiceRecorderDeviceID=None
        self.fullRecorderDeviceID=None
        self.amr=None

    def onRegState(self, prm):
        print ("***OnRegState: " + prm.reason)
    def onIncomingCall(self, prm):
        self.call_id==prm.callId
        self.acceptCall=True

        self.c = Call(self, call_id=prm.callId)
        
        ci = self.c.getInfo()
        msg = "Incoming call  from  '%s'" % (ci.remoteUri)
        print(msg)
            
        self.inCall=True


# pjsua2 test function
def pjsua2_test():
    # Create and initialize the library
    global ep
    ep_cfg = pj.EpConfig()
    ep_cfg.uaConfig.threadCnt = 0
    ep_cfg.uaConfig.mainThreadOnly = False
    ep = pj.Endpoint()
    ep.libCreate()
    ep.libInit(ep_cfg)

    # Create SIP transport. Error handling sample is shown
    sipTpConfig = pj.TransportConfig();
    sipTpConfig.port = 12345;
    tp=ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig);
    # Start the library
    ep.libStart();

    acfg = pj.AccountConfig();

    acfg.idUri = "sip:192.168.1.11:12345";

    # Create the account
    acc = Account(ep);
    acc.create(acfg)
    #Get device list and collect device IDs of two virtual devices created 
    ep.audDevManager().refreshDevs();
    devList=ep.audDevManager().enumDev()
    fullRecorderDeviceID=0
    devID=0
    for dev in devList:
        print(dev.name)
        if(dev.name=="FullRecorder"):
            acc.fullRecorderDeviceID=devID
            
        if(dev.name=="CallerVoice"):
            acc.callerVoiceRecorderDeviceID=devID
            ep.audDevManager().setPlaybackDev(acc.callerVoiceRecorderDeviceID);
            #acc.amr=ep.audDevManager().getPlaybackDevMedia()
            acc.amr = pj.AudioMediaRecorder.typecastFromAudioMedia(ep.audDevManager().getPlaybackDevMedia())
            acc.amr.createRecorder(file_name="123.wav");
            ep.mediaAdd(acc.amr)

        devID=devID+1
    ep.audDevManager().setPlaybackDev(acc.fullRecorderDeviceID);
        
            
    while True:
        ep.libHandleEvents(10)
        if(acc.acceptCall==True):
            acc.acceptCall=False;
            call_prm = pj.CallOpParam()
            call_prm.statusCode = 200
            acc.c.answer(call_prm) 
            if(acc.c.canConnectPlayer==True and acc.c.am!=None ):
                acc.c.canConnectPlayer=False
                player=pj.AudioMediaPlayer()
                #Play welcome message
                fn=u'/PJSUA2/example/welcomeFull.wav'
                player.createPlayer(fn, pj.PJMEDIA_FILE_NO_LOOP);
                # This will connect the sound device/mic to the call audio media
                player.startTransmit( acc.c.am);
                #player.startTransmit( ep.audDevManager().getPlaybackDevMedia());
                #ep.audDevManager().setPlaybackDev(self.acc.callerVoiceRecorderDeviceID);
                #player.startTransmit(acc.amr)
                """
                ep.audDevManager().refreshDevs();
                devList=ep.audDevManager().enumDev()
                devID=0
                for dev in devList:
                    print(dev.name)
                """

    ep.libDestroy()
    #del ep;

#
# main()
#
if __name__ == "__main__":
    #recorder=pj.AudioMediaRecorder()
    #recorder.createRecorder("123.wav");
    pjsua2_test();

  
  
  
  
  
  

 
