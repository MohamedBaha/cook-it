#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from snipsTools import SnipsConfigParser
from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import io
import paho.mqtt.client as mqtt

import sys
from threading import Timer
import time

import requests
import urllib
import json

CONFIG_INI = "config.ini"

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

OPEN_RECIPE 				= 'hermes/intent/GabOrange:openRecipe'
NEXT_STEP 					= 'hermes/intent/GabOrange:nextStep'
INGREDIENTS 				= 'hermes/intent/GabOrange:ingredients'
PREVIOUS_STEP 				= 'hermes/intent/GabOrange:previousStep'
REPEAT_STEP 				= 'hermes/intent/GabOrange:repeatStep'
ACTIVATE_TIMER 				= 'hermes/intent/GabOrange:activateTimer'

HERMES_ON_HOTWORD 			= 'hermes/hotword/default/detected'
HERMES_START_LISTENING 		= 'hermes/asr/startListening'
HERMES_SAY 					= 'hermes/tts/say'
HERMES_CAPTURED 			= 'hermes/asr/textCaptured'
HERMES_HOTWORD_TOGGLE_ON 	= 'hermes/hotword/toggleOn'


 def getRecetteFile(intent_message):    
		
        searchtermU = intentMessage.slots.mot_label.first().value
        searchterm = "{}".format(str(searchtermU.encode('utf-8')))
        #searchterm = "{}".format(str(intentMessage.slots.mot_label.first().value))

        baseUrl = u'http://' + server_address + u'/Cook_it/apirest/Informations/getSpecificRecette?idRecette='
        endUrl = u''
        finalurl = baseUrl + urllib.quote(searchterm) + endUrl

     	response= requests.get(finalurl)
	
	###recette
        recipe=response.json()
	###nom de la recette
	recipe_name=recette['name']
	
	###etapes
	ss=recipe['instruction(s)']
	etapes_list=[]
	for x in ss:
    		etapes.append(x['instruction'])
	etapes_string=''.join(etapes)
	
	print(etapes_string)
 	print '[Received] intent: {}'.format(intent_message.intent.intent_name)	
	
	return recipe, recipe_name,etapes_list,etapes_string

        print '[Received] intent: {}'.format(intent_message.intent.intent_name)


def onConnect(client, userData, flags, rc):
	mqtt.subscribe('hermes/intent/#')

	mqtt.subscribe(HERMES_ON_HOTWORD)
	mqtt.subscribe(HERMES_START_LISTENING)
	mqtt.subscribe(HERMES_SAY)
	mqtt.subscribe(HERMES_CAPTURED)
	mqtt.subscribe(HERMES_HOTWORD_TOGGLE_ON)
	mqttPublish.single('hermes/feedback/sound/toggleOn', payload=json.dumps({'siteId': 'default'}), hostname='127.0.0.1', port=1883)

def onMessage(client, userData, message): 
	
	# Parse the json response
   	#intent_json = json.loads(msg.payload)
    	#intentName = intent_json['intent']['intentName']
	
	intent = message.topic

	global recipe, currentStep, timers, confirm

	payload = json.loads(message.payload)
	sessionId = payload['sessionId']

	if intent == OPEN_RECIPE:
		if 'slots' not in payload:
			error(sessionId)
			return

		slotRecipeName = payload['slots'][0]['value']['value'].encode('utf-8')

		if recipe is not None and currentStep > 0:
			if confirm <= 0:
				confirm = 1
				endTalk(sessionId, text=['warningRecipeAlreadyOpen'])
				return
			else:
				for timer in timers:
					timer.cancel()

				timers = {}
				confirm = 0
				currentStep = 0

		#if os.path.isfile('./recipes/{}/{}.json'.format(settings.LANG, slotRecipeName.lower())):
		#	endTalk(sessionId, text=lang['confirmOpening'].format(payload['slots'][0]['rawValue']))
		currentStep = 0

		
		recipe,recipe_name = getRecetteFile(message)

		time.sleep(2)

		#timeType = lang['cookingTime'] if 'cookingTime' in recipe else lang['waitTime']
		#cookOrWaitTime = recipe['cookingTime'] if 'cookingTime' in recipe else recipe['waitTime']
		
		
		sentence="Pour préparer "
		hermes.publish_end_session(intent_message.session_id, etapes_string)
		"""for i in len(etapes):
			say(etapes[i])
			currentStep=currentStep+1"""
		else:
			endTalk(sessionId, text=lang['recipeNotFound'])

	elif intent == NEXT_STEP:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if str(currentStep + 1) not in recipe['steps']:
				endTalk(sessionId, text=lang['recipeEnd'])
			else:
				currentStep += 1
				step = recipe['steps'][str(currentStep)]

				ask = False
				if type(step) is dict and currentStep not in timers:
					ask = True
					step = step['text']

				endTalk(sessionId, text=lang['nextStep'].format(step))
				if ask:
					say(text=lang['timeAsk'])

	elif intent == INGREDIENTS:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			ss=recipe['ingrédients']
			ingredients=''
			for i in range(len(ss)):
    				sentence=''
   	 			sentence= str(ss[i]['quantité'])+" " + str(ss[i]['unité']) + ' de ' +str(ss[i]['label'])
    				ingredients+= u"{}. ".format(sentence)
				
			endTalk(sessionId, text=lang['neededIngredients'].format(recipe['name'], ingredients))

	elif intent == PREVIOUS_STEP:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if currentStep <= 1:
				endTalk(sessionId, text=lang['noPreviousStep'])
			else:
				currentStep -= 1
				step = recipe['instruction(s)'][currentStep]["instruction"]

				ask = False
				timer = 0
				if type(step) is dict and currentStep not in timers:
					ask = True
					timer = step['timer']
					step = step['text']

				endTalk(sessionId, text=lang['previousStepWas'].format(step))
				if ask:
					say(text=lang['hadTimerAsk'].format(timer))

	elif intent == REPEAT_STEP:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if currentStep <= 1:
				endTalk(sessionId, text=lang['nothingToSayNotStarted'])
			else:
				step = recipe['instruction(s)'][currentStep]["instruction"]
				endTalk(sessionId, text=lang['repeatStep'].format(step))

	elif intent == ACTIVATE_TIMER:
		if recipe is None:
			endTalk(sessionId, text=lang['noTimerNotStarted'])
		else:
			step = recipe['instruction(s)'][currentStep]["instruction"]

			if type(step) is not dict:
				endTalk(sessionId, text=lang['notTimerForThisStep'])
			elif currentStep in timers:
				endTalk(sessionId, text=lang['timerAlreadyRunning'])
			else:
				timer = Timer(int(step['timer']), onTimeUp, args=[currentStep, step])
				timer.start()
				timers[currentStep] = timer
				endTalk(sessionId, text=lang['timerConfirm'])


#class action(object):
   """Class used to wrap action code with mqtt connection
        
        Please change the name refering to your application
    """

"""    def __init__(self):
        # get the configuration if needed
        try:
            self.config = SnipsConfigParser.read_configuration_file(CONFIG_INI)
        except :
            self.config = None

        # start listening to MQTT
        self.start_blocking()"""
        
    # --> Sub callback function, one per intent
   

  #  def intent_2_callback(self, hermes, intent_message):
        # terminate the session first if not continue
  #      hermes.publish_end_session(intent_message.session_id, "")

        # action code goes here...
  #     print '[Received] intent: {}'.format(intent_message.intent.intent_name)

        # if need to speak the execution result by tts
   #    hermes.publish_start_session_notification(intent_message.site_id, 
   #                                               "Action2 has been done")

    # More callback function goes here...

    # --> Master callback function, triggered everytime an intent is recognized
    #def master_intent_callback(self,hermes, intent_message):
    #    coming_intent = intent_message.intent.intent_name
    #    if coming_intent == 'intent_1':
    #        self.intent_1_callback(hermes, intent_message)
    #    if coming_intent == 'intent_2':
    #        self.intent_2_callback(hermes, intent_message)

        # more callback and if condition goes here...

    # --> Register callback function and start MQTT

def error(sessionId):
	endTalk(sessionId, lang['error'])

def endTalk(sessionId, text):
	mqttClient.publish('hermes/dialogueManager/endSession', json.dumps({
		'sessionId': sessionId,
		'text': text
	}))

def say(text):
	mqttClient.publish('hermes/dialogueManager/startSession', json.dumps({
		'init': {
			'type': 'notification',
			'text': text
		}
	}))

def onTimeUp(*args, **kwargs):
	global timers
	wasStep = args[0]
	step = args[1]
	del timers[wasStep]
	say(text=lang['timerEnd'].format(step['textAfterTimer']))


mqttClient = None
leds = None
running = True
recipe = None
currentStep = 0
timers = {}
confirm = 0
lang = ''

logger = logging.getLogger('MyChef')
logger.addHandler(logging.StreamHandler())

if __name__ == '__main__':

	mqttClient = mqtt.Client()
	mqttClient.on_connect = onConnect
	mqttClient.on_message = onMessage
	mqttClient.connect('localhost', 1883)
	logger.info(lang['appReady'])
	mqttClient.loop_start()
	try:
		while running:
			time.sleep(0.1)
	except KeyboardInterrupt:
		mqttClient.loop_stop()
		mqttClient.disconnect()
		running = False
	finally:
		logger.info(lang['stopping'])
