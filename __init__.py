"""A Mycroft skill to provide information about movies.

The information is sourced from The Movie Database (TMDb) API.  Documentation
for this API can be found at https://www.themoviedb.org/.  The API is free to
use.  It can be accessed using the API key specified in the __api__ variable
or by an API specified by the user in skill settings.
"""
from datetime import datetime
import os
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.format import pronounce_number, nice_date, nice_number
from mycroft.util.log import LOG

import tmdbv3api

DEFAULT_API_KEY = "6b064259b900f7d4fd32f3c74ac35207"

LOGGER = LOG(__name__)

TMDB = tmdbv3api.TMDb()
MOVIE = tmdbv3api.Movie()


class MovieMaster(MycroftSkill):
	def __init__(self):
		super(MovieMaster, self).__init__(name="MovieMaster")
		self.search_depth = None
		self.movie_db = tmdbv3api.TMDb()
		self.movie = tmdbv3api.Movie()

	def initialize(self):
		"""Set some variables that do not change during the execution of the script"""
		self.apply_user_settings()
		self.movie_db.language = self.lang
		self.settings_change_callback = self.apply_user_settings

	def apply_user_settings(self):
		"""Apply user-defined settings from https://home.mycroft.ai.

		The API key defined at the top of this file can be overridden by the
		user if they have their own.  The search depth is used to limit the
		number of search results included in a response to the user.  For
		example, if there are 10 movies on the popular movies list and search
		depth is set to 5, only five movies will be included in response
		"""
		self._determine_api_key()
		self.searchDepth = self.settings.get("searchDepth")

	def _determine_api_key(self):
		"""Use the API key in settings, if provided.  Otherwise use developer key."""
		settings_api_key = self.settings.get("apiv3")
		if settings_api_key in ("Default", "", None):
			self.movie_db.api_key = DEFAULT_API_KEY
		else:
			self.movie_db.api_key = settings_api_key
			try:
				# Make a call to the API to verify the key
				self.movie.popular()
			except Exception:
				self.log.exception(
					'API Key {} invalid. Reverting to default'.format(settings_api_key)
				)
				self.movie_db.api_key = DEFAULT_API_KEY

	@intent_file_handler("movie.description.intent")
	def handle_movie_description(self, message):
		""" Gets the long version of the requested movie.
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0])
			if movieDetails.overview is not "":
				self.speak_dialog("movie.description", {"movie": movie})
				for sentence in movieDetails.overview.split(". "):
					self.speak(sentence)
			else:
				self.speak_dialog("no.info", {"movie": movie})

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.information.intent")
	def handle_movie_information(self, message):
		""" Gets the short version and adds the TagLine for good measure.
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0].id)
			self.speak_dialog("movie.info.response", {"movie": movieDetails.title, "year": nice_date(datetime.strptime(movieDetails.release_date.replace("-", " "), "%Y %m %d")), "budget": nice_number(movieDetails.budget)})
			self.speak(movieDetails.tagline)

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.year.intent")
	def handle_movie_year(self, message):
		""" Gets the year the movie was released.
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0].id)
			self.speak_dialog("movie.year", {"movie": movieDetails.title, "year": nice_date(datetime.strptime(movieDetails.release_date.replace("-", " "), "%Y %m %d"))})

		## If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.cast.intent")
	def handle_movie_cast(self, message):
		""" Gets the cast of the requested movie.

		The search_depth setting is avaliable at home.mycroft.ai
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0].id)
			cast = movieDetails.casts["cast"][:self.searchDepth]

			# Create a list to store the cast to be included in the dialog
			actorList = ""
			# Get the last actor in the list so that the dialog can say it properly
			lastInList = cast.pop()
			lastActor = " {} as {}".format(lastInList["name"], lastInList["character"])
			# Format the rest of the list for the dialog
			for person in cast:
				actor = " {} as {},".format(person["name"], person["character"])
				# Add the formated sentence to the actor list
				actorList = actorList + actor
			self.speak_dialog("movie.cast", {"movie": movie, "actorlist": actorList, "lastactor": lastActor})

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.production.intent")
	def handle_movie_production(self, message):
		""" Gets the production companies that made the movie.

		The search_depth setting is avaliable at home.mycroft.ai
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0].id)
			companyList = movieDetails.production_companies[:self.searchDepth]

			# If there is only one production company, say the dialog differently
			if len(companyList) == 1:
				self.speak_dialog("movie.production.single", {"movie": movie, "company": companyList[0]["name"]})
			# If there is more, get the last in the list and set up the dialog
			if len(companyList) > 1:
				companies = ""
				lastCompany = companyList.pop()["name"]
				for company in companyList:
					companies = companies + company["name"] + ", "
				self.speak_dialog("movie.production.multiple", {"companies": companies, "movie": movie, "lastcompany": lastCompany})

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.genres.intent")
	def handle_movie_genre(self, message):
		""" Gets the genres the movie belongs to.

		The search_depth setting is avaliable at home.mycroft.ai
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0].id)
			genreList = movieDetails.genres[:self.searchDepth]
			# Set up dialog AGAIN just like above.  Is there a better way?
			if len(genreList) == 1:
				self.speak_dialog("movie.genre.single", {"movie": movie, "genre": genreList[0]["name"]})
			if len(genreList) > 1:
				genreDialog = ""
				lastGenre = genreList.pop()["name"]
				for genre in genreList:
					genreDialog = genreDialog + genre["name"] + ", "
				self.speak_dialog("movie.genre.multiple", {"genrelist": genreDialog, "genrelistlast": lastGenre})

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.runtime.intent")
	def handle_movie_length(self, message):
		""" Gets the runtime of the searched movie.
		"""
		movie = message.data.get("movie")
		try:
			movieDetails = MOVIE.details(MOVIE.search(movie)[:1][0].id)
			self.speak_dialog("movie.runtime", {"movie": movie, "runtime": movieDetails.runtime})

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie})

	@intent_file_handler("movie.recommendations.intent")
	def handle_movie_recommendations(self, message):
		""" Gets the top movies that are similar to the suggested movie.
		"""
		try:
			movie = message.data.get("movie")
			
			# Create a list to store the dialog
			movieDialog = ""
			movieRecommendations = MOVIE.recommendations(MOVIE.search(movie)[:1][0].id)[:self.searchDepth]
			# Get the last movie
			lastMovie = movieRecommendations.pop()
			for film in movieRecommendations:
				if movieDialog == "":
					movieDialog = film.title
				else:
					movieDialog = movieDialog + ", " + film.title
			movieDialog = movieDialog + " and {}".format(lastMovie.title)
			self.speak_dialog("movie.recommendations", {"movielist": movieDialog, "movie": movie})

		# If the title can not be found, it creates an IndexError
		except IndexError:
			self.speak_dialog("no.info", {"movie": movie.title})

	@intent_file_handler("movie.popular.intent")
	def handle_popular_movies(self, message):
		""" Gets the daily popular movies.

		The list changes daily, and are not just recent movies.

		The search_depth setting is avaliable at home.mycroft.ai
		"""
		try:
			movie = message.data.get("movie")
			popularMovies = MOVIE.popular()[:self.searchDepth]
			# Lets see...I think we will set up the dialog again.
			lastMovie = popularMovies.pop()
			popularDialog = ""
			for movie in popularMovies:
				if popularDialog == "":
					popularDialog = movie.title
				else:
					popularDialog = popularDialog + ", " + movie.title
			popularDialog = popularDialog + " and {}".format(lastMovie.title)
			self.speak_dialog("movie.popular", {"popularlist": popularDialog})

		except:
			self.speak_dialog("no.info", {"movie": movie.title})
			pass

	@intent_file_handler("movie.top.intent")
	def handle_top_movies(self, message):
		""" Gets the top rated movies of the day.
		The list changes daily, and are not just recent movies.

		The search_depth setting is avaliable at home.mycroft.ai
		"""
		try:
			movie = message.data.get("movie")
			topMovies = MOVIE.top_rated()[:self.searchDepth]
			# Set up the dialog
			lastMovie = topMovies.pop()
			topDialog = ""
			for movie in topMovies:
				if topDialog == "":
					topDialog = movie.title
				else:
					topDialog = topDialog + ", {}".format(movie.title)
			topDialog = topDialog + " and {}".format(lastMovie.title)
			self.speak_dialog("movie.top", {"toplist": topDialog})

		except:
			self.speak_dialog("no.info", {"movie": movie.title})
			pass

def create_skill():
	return MovieMaster()
