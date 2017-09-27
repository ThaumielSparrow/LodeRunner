import os
import sys

from code.tools.xml import XMLParser
from code.utils.common import generate_string_id, log, log2, logn


# Local constant
DEFAULT_LAYOUT_NAME = "default"


class LocalizationController:

	def __init__(self):

		# Track preferred language
		self.language = "en"

		# Track layout associated with this language.
		# Layout determines how certain widgets (game over menu, etc.)
		# might appear on the screen.
		self.layout = DEFAULT_LAYOUT_NAME


		# Track loaded translations, hashed by original string uid
		self.translations = {}


		# Save a catalogue of simple, "common" strings that we can requested
		# by a human-readable name (fake example:  save-successful = "Save successful!")
		self.common_labels = {}


	# Set preferred language
	def set_language(self, language):

		# Set
		self.language = language


	# Get preferred language
	def get_language(self):

		# Return
		return self.language


	# Set layout
	def set_layout(self, layout):

		# Set
		self.layout = layout


	# Set layout to default
	def set_layout_to_default(self):

		# Default set
		self.layout = DEFAULT_LAYOUT_NAME


	# Get layout
	def get_layout(self):

		# Return
		return self.layout


	# Load localization data from a given file
	def load(self, filename):

		# Validate path
		if ( os.path.exists(filename) ):

			# Parse xml
			root = XMLParser().create_node_from_file(filename)

			# Validate parsing
			if (root):

				# Find strings ref
				ref_strings = root.find_node_by_tag("strings")

				# Validate
				if (ref_strings):

					# Loop categories
					for ref_category in ref_strings.get_nodes_by_tag("*"):

						# Loop defined translations
						for ref_string in ref_category.get_nodes_by_tag("*"):

							# tag name is the string uid
							uid = ref_string.tag_type

							# Hash translation
							self.translations[uid] = ref_string.innerText


	# Unload localization data, according to a given file's translations
	def unload(self, filename):

		# Validate path
		if ( os.path.exists(filename) ):

			# Parse xml
			root = XMLParser().create_node_from_file(filename)

			# Validate parsing
			if (root):

				# Find strings ref
				ref_strings = root.find_node_by_tag("strings")

				# Validate
				if (ref_strings):

					# Loop categories
					for ref_category in ref_strings.get_nodes_by_tag("*"):

						# Loop defined translations
						for ref_string in ref_category.get_nodes_by_tag("*"):

							# tag name is the string uid
							uid = ref_string.tag_type

							# Remove translation from hash
							self.translations.pop(uid)


	# Unload all localization data (default language)
	def clear(self):

		# Goodbye to all translations!
		self.translations.clear()


	# Import common label/string data from a given file
	def import_labels(self, filename):

		# Validate path
		if ( os.path.exists(filename) ):

			# Parse xml
			root = XMLParser().create_node_from_file(filename)

			# Validate parsing
			if (root):

				# Find strings ref
				ref_strings = root.find_node_by_tag("strings")

				# Validate
				if (ref_strings):

					# Loop categories.  I don't store by category, but I keep the constants
					# in at least one category (to parallel all other translation files).
					for ref_category in ref_strings.get_nodes_by_tag("*"):

						# Loop simple list
						for ref_string in ref_category.get_nodes_by_tag("string"):

							# Get name identifier, then get label text data
							(name, value) = (
								ref_string.get_attribute("name"),
								ref_string.innerText
							)

							# Save this common label
							self.common_labels[name] = value


	# Get a common label by its name.
	# Optionally supply a hash of parameters.
	def get_label(self, name, params = {}):

		# Validate name
		if (name in self.common_labels):

			# Get translation
			s = self.translate( self.common_labels[name] )

			# Substitute parameters
			for key in params:

				# Substitute
				s = s.replace(key, "%s" % params[key])

			# Return label data
			return s

		# Not found
		else:
			return "%s" % name


	# Clear all previously loaded data
	def clear(self):

		# Clear
		self.translations.clear()


	# Fetch translation for a given string
	def translate(self, s):

		# Generate string uid
		uid = generate_string_id(s)

		logn( "localization", "Seeking:  %s\n\t'%s'\n\n" % (uid, s) )

		# Search for translation
		if ( uid in self.translations ):

			logn( "localization", "Found:  %s\n" % self.translations[uid] )
			# Return translation
			return self.translations[uid]

		# Debug info
		else:
			logn( "localization error", "No translation:  '%s'\n" % s )


		# Default to original string
		return s