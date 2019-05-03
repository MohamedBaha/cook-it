#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from snipsTools import SnipsConfigParser
from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import io

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

def onConnect(client, userData, flags, rc):
	mqttClient.subscribe(OPEN_RECIPE)
	mqttClient.subscribe(NEXT_STEP)
	mqttClient.subscribe(INGREDIENTS)
	mqttClient.subscribe(PREVIOUS_STEP)
	mqttClient.subscribe(REPEAT_STEP)
	mqttClient.subscribe(ACTIVATE_TIMER)

	mqttClient.subscribe(HERMES_ON_HOTWORD)
	mqttClient.subscribe(HERMES_START_LISTENING)
	mqttClient.subscribe(HERMES_SAY)
	mqttClient.subscribe(HERMES_CAPTURED)
	mqttClient.subscribe(HERMES_HOTWORD_TOGGLE_ON)
	mqttPublish.single('hermes/feedback/sound/toggleOn', payload=json.dumps({'siteId': 'default'}), hostname='127.0.0.1', port=1883)

def onMessage(client, userData, message):
	global lang

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
				endTalk(sessionId, text=lang['warningRecipeAlreadyOpen'])
				return
			else:
				for timer in timers:
					timer.cancel()

				timers = {}
				confirm = 0
				currentStep = 0

		if os.path.isfile('./recipes/{}/{}.json'.format(settings.LANG, slotRecipeName.lower())):
			endTalk(sessionId, text=lang['confirmOpening'].format(payload['slots'][0]['rawValue']))
			currentStep = 0

			file = codecs.open('./recipes/{}/{}.json'.format(settings.LANG, slotRecipeName.lower()), 'r', encoding='utf-8')
			string = file.read()
			file.close()
			recipe = json.loads(string)

			time.sleep(2)

			recipeName = recipe['name'] if 'phonetic' not in recipe else recipe['phonetic']
			timeType = lang['cookingTime'] if 'cookingTime' in recipe else lang['waitTime']
			cookOrWaitTime = recipe['cookingTime'] if 'cookingTime' in recipe else recipe['waitTime']

			say(text=lang['recipePresentation'].format(
				recipeName,
				recipe['difficulty'],
				recipe['person'],
				recipe['totalTime'],
				recipe['preparationTime'],
				cookOrWaitTime,
				timeType
			))
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
			ingredients = ''
			for ingredient in recipe['ingredients']:
				ingredients += u"{}. ".format(ingredient)

			endTalk(sessionId, text=lang['neededIngredients'].format(recipe['name'], ingredients))

	elif intent == PREVIOUS_STEP:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if currentStep <= 1:
				endTalk(sessionId, text=lang['noPreviousStep'])
			else:
				currentStep -= 1
				step = recipe['steps'][str(currentStep)]

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
				step = recipe['steps'][str(currentStep)]
				endTalk(sessionId, text=lang['repeatStep'].format(step))

	elif intent == ACTIVATE_TIMER:
		if recipe is None:
			endTalk(sessionId, text=lang['noTimerNotStarted'])
		else:
			step = recipe['steps'][str(currentStep)]

			if type(step) is not dict:
				endTalk(sessionId, text=lang['notTimerForThisStep'])
			elif currentStep in timers:
				endTalk(sessionId, text=lang['timerAlreadyRunning'])
			else:
				timer = Timer(int(step['timer']), onTimeUp, args=[currentStep, step])
				timer.start()
				timers[currentStep] = timer
				endTalk(sessionId, text=lang['timerConfirm'])


class action(object):
    """Class used to wrap action code with mqtt connection
        
        Please change the name refering to your application
    """

    def __init__(self):
        # get the configuration if needed
        try:
            self.config = SnipsConfigParser.read_configuration_file(CONFIG_INI)
        except :
            self.config = None

        # start listening to MQTT
        self.start_blocking()
        
    # --> Sub callback function, one per intent
    def openrecipe(self, hermes, intent_message):
        # terminate the session first if not continue
        hermes.publish_end_session(intent_message.session_id, "")
        
        # action code goes here...
        searchtermU = intentMessage.slots.mot_label.first().value
        searchterm = "{}".format(str(searchtermU.encode('utf-8')))
        #searchterm = "{}".format(str(intentMessage.slots.mot_label.first().value))

        baseUrl = u'http://' + server_address + u'/Cook_it/apirest/DuringRecette/recetteStart?idRecette='
        endUrl = u''
        finalurl = baseUrl + urllib.quote(searchterm) + endUrl

        requests.get(finalurl)
        response = requests.get('http://' + server_address + '/Cook_it/apirest/DuringRecette/getCurrentInstruction')

        output = response.text
        json_output = json.loads(output)

        result_sentence = u'Démarrage de la recette de %s. Étape %s : %s' % (json_output[u'recetteLabel'], json_output[u'step'], json_output[u'description'])

        current_session_id = intentMessage.session_id
        hermes.publish_end_session(current_session_id, result_sentence)
        
        ##print '[Received] intent: {}'.format(intent_message.intent.intent_name)

        # if need to speak the execution result by tts
        hermes.publish_start_session_notification(intent_message.site_id,
                                                    "Action1 has been done")

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
    def master_intent_callback(self,hermes, intent_message):
        coming_intent = intent_message.intent.intent_name
        if coming_intent == 'intent_1':
            self.intent_1_callback(hermes, intent_message)
        if coming_intent == 'intent_2':
            self.intent_2_callback(hermes, intent_message)

        # more callback and if condition goes here...

    # --> Register callback function and start MQTT
    def start_blocking(self):
        with Hermes(MQTT_ADDR) as h:
            h.subscribe_intents(self.master_intent_callback).start()

if __name__ == "__main__":
    Template()
