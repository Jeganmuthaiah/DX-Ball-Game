import direct.directbase.DirectStart
from panda3d.core import TextNode
from panda3d.core import Point2,Point3,Vec3,Vec4
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from direct.task.Task import Task
from math import sin, cos, pi
from random import randint, choice, random
from direct.interval.MetaInterval import Sequence
from direct.interval.FunctionInterval import Wait,Func
import cPickle, sys

#environ = loader.loadModel("models/plane")
#environ.reparentTo(render)
#environ.setScale(2,2,2)
#environ.setPos(0,0,0)

#Load the panda actor, and loop its animation
#pandaActor = Actor.Actor("models/ralph",{"walk":"models/ralph-walk"})
##pandaActor.setScale(0.005,0.005,0.005)
#pandaActor.reparentTo(render)
#pandaActor.loop("walk")

SPRITE_POS = 55     #At default field of view and a depth of 55, the screen
                    #dimensions is 40x30 units
SCREEN_X = 20       #Screen goes from -20 to 20 on X
SCREEN_Y = 15       #Screen goes from -15 to 15 on Y
TURN_RATE = 60  #Degrees ship can turn in 1 second
ACCELERATION = 10   #Ship acceleration in units/sec/sec
MAX_VEL = 6         #Maximum ship velocity in units/sec
MAX_VEL_SQ = MAX_VEL ** 2  #Square of the ship velocity
DEG_TO_RAD = pi/180 #translates degrees to radians for sin and cos
BULLET_LIFE = 2     #How long bullets stay on screen before removed
BULLET_REPEAT = .2  #How often bullets can be fired
BULLET_SPEED = 10   #Speed bullets move
AST_INIT_VEL = 1    #Velocity of the largest asteroids
BRI_INIT_SCALE = 1  #Initial asteroid scale
AST_VEL_SCALE = 2.2 #How much asteroid speed multiplies when broken up
AST_SIZE_SCALE = .6 #How much asteroid scale changes when broken up
AST_MIN_SCALE = 1.1 #If and asteroid is smaller than this and is hit,
                    #it disapears instead of splitting up
BALL_INIT_SCALE=1
BOARD_INIT_SCALE=4

#dt=0
def genLabelText(text, i):
  return OnscreenText(text = text, pos = (-1.3, .95-.05*i), fg=(1,1,0,1),
                      align = TextNode.ALeft, scale = .05)


#Run the tutorial
def loadObject(tex = None, pos = Point2(0,0), depth = SPRITE_POS, scale = 1,
               transparency = True):
  obj = loader.loadModel("models/plane") #Every object uses the plane model
  obj.reparentTo(camera)              #Everything is parented to the camera so
                                      #that it faces the screen
  obj.setPos(Point3(pos.getX(), depth, pos.getY())) #Set initial position
  
  obj.setScale(scale)                 #Set initial scale
  obj.setBin("unsorted", 0)           #This tells Panda not to worry about the
                                      #order this is drawn in. (it prevents an
                                      #effect known as z-fighting)
  obj.setDepthTest(False)             #Tells panda not to check if something
                                      #has already drawn in front of it
                                      #(Everything in this game is at the same
                                      #depth anyway)
  if transparency: obj.setTransparency(1) #All of our objects are trasnparent
  if tex:
    tex = loader.loadTexture("textures/"+tex+".png") #Load the texture
    obj.setTexture(tex, 1)                           #Set the texture

  return obj

class World(DirectObject):
  def __init__(self):
    #This code puts the standard title and instruction text on screen
    self.title = OnscreenText(text="DX-Ball Game",
                              style=1, fg=(1,1,0,1),
                              pos=(0.8,-0.95), scale = .07)
    self.escapeText =   genLabelText("ESC: Quit", 0)
    self.leftkeyText =  genLabelText("[Left Arrow]: Move Left", 1)
    self.rightkeyText = genLabelText("[Right Arrow]: Move Right", 2)
    self.spacekeyText = genLabelText("[Space Bar]: Fire Ball", 3)

    self.keys = {"turnLeft" : 0, "turnRight": 0,
                 "accel": 0, "fire": 0}

    self.accept("escape", sys.exit)            #Escape quits
    #Other keys events set the appropriate value in our key dictionary
    self.accept("arrow_left",     self.setKey, ["turnLeft", 1])
    self.accept("arrow_left-up",  self.setKey, ["turnLeft", 1])
    self.accept("arrow_right",    self.setKey, ["turnRight", 1])
    self.accept("arrow_right-up", self.setKey, ["turnRight", 1])
    self.accept("arrow_up",       self.setKey, ["accel", 1])
    self.accept("arrow_up-up",    self.setKey, ["accel", 1])
    self.accept("space",          self.setKey, ["fire", 1])

    #base.disableMouse()       #Disable default mouse-based camera control
    self.bg = loadObject("stars", scale = 146, depth = 200,
                         transparency = False) #Load the background starfield

    self.ship = loadObject("boardfinal",pos=Point2(0,-13),scale=BOARD_INIT_SCALE)
    
    self.ball = loadObject("ball",pos=Point2(0,-10),scale=BALL_INIT_SCALE)
    self.setVelocity(self.ball, Vec3(0,0,0))    #Initial velocity
    self.bricks=[]
    for i in range(-18,19,2):
      for j in range(8,12,1):
        self.bricks.append(loadObject("brickfinal",pos=Point2(i,j),scale=BRI_INIT_SCALE))
    #As described earlier, this simply sets a key in the self.keys dictionary to
    #self.setExpires(self.ball,0)

    self.alive=True
    #the given value
    self.gameTask = taskMgr.add(self.gameLoop, "gameLoop")  
    self.gameTask.last = 0         #Task time of the last frame
  def setExpires(self, obj, val):
      obj.setTag("expires", str(val))
    
  def getExpires(self, obj):
      return float(obj.getTag("expires"))

  def gameLoop(self, task):
      #task contains a variable time, which is the time in seconds the task has
      #been running. By default, it does not have a delta time (or dt), which is
      #the amount of time elapsed from the last frame. A common way to do this is
      #to store the current time in task.last. This can be used to find dt
      
      #dt = task.time - task.last
      dt=0.3
      dta=1
      task.last = task.time
      #If the ship is not alive, do nothing. Tasks return Task.cont to signify
      #that the task should continue running. If Task.done were returned instead,
      #the task would be removed and would no longer be called every frame
      if not self.alive: return Task.cont
      #print "inside task"
      #update ship position
      self.updateShip(dt)
      heading_r = self.ball.getR()
      global TURN_RATE
      if self.keys["fire"]:
          heading_r = dta * TURN_RATE
          #self.ball.setR(heading_r %360)
          #self.ball.setZ(heading_r)
          heading_rad = DEG_TO_RAD * heading_r
          #This builds a new velocity vector and adds it to the current one
          #Relative to the camera, the screen in Panda is the XZ plane.
          #Therefore all of our Y values in our velocities are 0 to signify no
          #change in that direction
          newVel = (
            Vec3(sin(heading_rad), 0, cos(heading_rad)) * ACCELERATION * dta)
          newVel += self.getVelocity(self.ball)
          #Clamps the new velocity to the maximum speed. lengthSquared() is used
          #again since it is faster than length()
          if newVel.lengthSquared() > MAX_VEL_SQ:
            newVel.normalize()
            newVel *= MAX_VEL
          self.setVelocity(self.ball, newVel)
      

      if len(self.bricks)==0:
        self.alive=False
        self.title = OnscreenText(text="You Win",
                              style=1, fg=(1,1,0,1),
                              pos=(0,0), scale = .1)


      for i in range(len(self.bricks)-1, -1, -1):
        #Panda's collision detection is more complicated than we need here.
        #This is the basic sphere collision check. If the distance between
        #the object centers is less than sum of the radii of the two objects,
        #then we have a collision. We use lengthSquared since it is a quicker
        #vector operation than length
        if ((self.ball.getPos() - self.bricks[i].getPos()).lengthSquared() <
            (((self.ball.getScale().getX() + self.bricks[i].getScale().getX())
              * .5 ) ** 2)):
          self.bricks[i].remove()   
          self.bricks = self.bricks[:i]+self.bricks[i+1:]
          #print TURN_RATE
          if TURN_RATE==90 or TURN_RATE==-90 or TURN_RATE==0 or TURN_RATE==180 or TURN_RATE==-180:
            TURN_RATE=randint(30,60)
          elif TURN_RATE>0 and TURN_RATE<90:
            TURN_RATE=90+TURN_RATE
          elif TURN_RATE<0 and TURN_RATE>-90:
            TURN_RATE-=90
          elif TURN_RATE>90 and TURN_RATE<180:
            TURN_RATE-=90
          elif TURN_RATE<-90 and TURN_RATE>-180:
            TURN_RATE=90
          #print TURN_RATE
          break
          #self.bricks[i]    #Schedule the bullet for removal
        #  self.asteroidHit(i)      #Handle the hit

      #Finally, update the position as with any other object
       # print self.bricks[i].getPos();
      #self.updatePos(self.ball, dt)
      
      if ((self.ball.getPos() - self.ship.getPos()).lengthSquared() <
          (((self.ball.getScale().getX() + self.ship.getScale().getX())
            * .5 ) ** 2)):
        print TURN_RATE
        if TURN_RATE==90 or TURN_RATE==-90 or TURN_RATE==0 or TURN_RATE==180 or TURN_RATE==-180:
          TURN_RATE=randint(30,60)
        elif TURN_RATE>90 and TURN_RATE<180:
          TURN_RATE=TURN_RATE-90
        elif TURN_RATE<-90 and TURN_RATE>-180:
          TURN_RATE+=180
        else:
          TURN_RATE=-TURN_RATE
        print TURN_RATE
      self.updatePos(self.ball, dt)
      return Task.cont


  def setKey(self, key, val):
   # self.bricks[0].remove()
    print "set_key"
    self.keys[key] = val
    dt=0.3

  def setVelocity(self, obj, val):
    list = [val[0], val[1], val[2]]
    obj.setTag("velocity", cPickle.dumps(list))

  def getVelocity(self, obj):
      list = cPickle.loads(obj.getTag("velocity"))
      return Vec3(list[0], list[1], list[2])

  def updateShip(self, dt):
      #print dt
     # print 
      heading = self.ship.getX() #Heading is the roll value for this model
      #Change heading if left or right is being pressed
      if self.keys["turnLeft"]:
        heading -= dt * 5
        self.ship.setX(heading)
        self.keys["turnLeft"]=0

      elif self.keys["turnRight"]:
        heading+=dt*5
        self.ship.setX(heading)
        self.keys["turnRight"]=0

      
          #self.fire(task.time)  #If so, call the fire function
          #And disable firing for a bit
          #task.nextBullet = task.time + BULLET_REPEAT  
        #self.keys["fire"] = 0   #Remove the fire flag until the next spacebar press


    #Thrust causes acceleration in the direction the ship is currently facing
      # if self.keys["turnLeft"] or self.keys["turnRight"]:
      #   print "inside if"
      #   heading_rad = DEG_TO_RAD * heading
      #   #This builds a new velocity vector and adds it to the current one
      #   #Relative to the camera, the screen in Panda is the XZ plane.
      #   #Therefore all of our Y values in our velocities are 0 to signify no
      #   #change in that direction
      #   newVel = (
      #     Vec3(sin(heading_rad), 0, cos(heading_rad)) * ACCELERATION * dt)
      #   newVel += self.getVelocity(self.ship)
      #   #Clamps the new velocity to the maximum speed. lengthSquared() is used
      #   #again since it is faster than length()
      #   if newVel.lengthSquared() > MAX_VEL_SQ:
      #     newVel.normalize()
      #     newVel *= MAX_VEL
      #   self.setVelocity(self.ship, newVel)
    
    #Finally, update the position as with any other object
#      self.updatePos(self.ship, dt)

  def updatePos(self, obj, dt):
      vel = self.getVelocity(obj)
      newPos = obj.getPos() + (vel*.05)
      #print "inside updatePos"
      #Check if the object is out of bounds. If so, wrap it
      radius = .75 * obj.getScale().getX()
      global TURN_RATE
      if newPos.getX() - radius > SCREEN_X-1: 
        #print TURN_RATE
        #newPos.setZ(SCREEN_Y)
        if TURN_RATE==90 or TURN_RATE==-90 or TURN_RATE==0 or TURN_RATE==180 or TURN_RATE==-180:
          TURN_RATE=randint(30,60)
        elif TURN_RATE>0 and TURN_RATE<90:
          TURN_RATE=-TURN_RATE

        elif TURN_RATE>90 and TURN_RATE<=180:
          TURN_RATE=-TURN_RATE
        #print TURN_RATE       
      elif newPos.getX() + radius < -SCREEN_X+1:
        #print "updatePos elif of X %d" %TURN_RATE
        #newPos.setX(SCREEN_X)
        if TURN_RATE==90 or TURN_RATE==-90 or TURN_RATE==0 or TURN_RATE==180 or TURN_RATE==-180:
          TURN_RATE=randint(30,60)
        elif TURN_RATE<0 and TURN_RATE>-90:
          #TURN_RATE=90+TURN_RATE
          TURN_RATE=-TURN_RATE
        elif TURN_RATE<-90 and TURN_RATE>=-180:
          #TURN_RATE-=180
          TURN_RATE=-TURN_RATE
        #print TURN_RATE
      if newPos.getZ() - radius > SCREEN_Y-1: 
        #print "updatePos if of Y"
        #newPos.setZ(-SCREEN_Y)
        if TURN_RATE==90 or TURN_RATE==-90 or TURN_RATE==0 or TURN_RATE==180 or TURN_RATE==-180:
          TURN_RATE=randint(30,60)
        elif TURN_RATE>0 and TURN_RATE<90:
          #TURN_RATE=TURN_RATE+90
          TURN_RATE=180-TURN_RATE
        elif TURN_RATE<0 and TURN_RATE>-90:
          #TURN_RATE-=90
          TURN_RATE=TURN_RATE-90
          #TURN_RATE+=180
        #print TURN_RATE
      elif newPos.getZ() + radius < -SCREEN_Y: 
        #print "updatePos elif of Y"
        #newPos.setZ(SCREEN_Y)
        #TURN_RATE=90+TURN_RATE
        self.alive=False
        self.title = OnscreenText(text="Game Over",
                              style=1, fg=(1,1,0,1),
                              pos=(0,0), scale = .1)

      obj.setPos(newPos)

 


w = World()
run()