#!/usr/bin/env python
#  Arturo scrapes, downloads and renames TV series subtitles for you.
#  Copyright 2009, Michele Trimarchi

#  Arturo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  Arturo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with Arturo. If not, see <http://www.gnu.org/licenses/>.

"""Arturo scrapes, downloads and renames TV series subtitles for you."""
import urllib2
import re
import zipfile
import os
import sys
import logging
import shutil
import urlparse
import tempfile
import cgi
import ConfigParser
LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_LEVEL = 'INFO'
LOG_DICT = {'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL}
VIDEO_FILE_TYPE = 0
SUBTITLE_FILE_TYPE = 1
ZIP_FILE_TYPE = 0
RAR_FILE_TYPE = 1
TEXT_FILE_TYPE = 2
UNKNOWN_FILE_TYPE = 3

EMPTY_EPISODE = '00'
EMPTY_SEASON = '00'
__version__ = '0.9'


class Arturo(object):
    """Main class that serves your subtitles"""
    def __init__(self, install_dir):
        self.install_dir = install_dir
        sys.path.insert(0, os.path.join(self.install_dir, 'plugins'))
        if not os.path.isdir(os.path.join(self.install_dir, 'log')):
            os.mkdir(os.path.join(self.install_dir, 'log'))
        logging.basicConfig(filename = os.path.join(self.install_dir,
                                                    'log',
                                                    'arturo.log'),
                            level = LOG_DICT[DEFAULT_LOG_LEVEL],
                            format = LOGGING_FORMAT)
        self.settings = self._load_config()
        logger = logging.getLogger()
        logger.setLevel(LOG_DICT[self.settings.program_settings.log_level])
        print("Arturo is READY to start!")
        logging.info("Arturo is READY to start!")

    def _load_config(self):
        """Load configuration from file and return a settings object"""
        try:
            tvseries_settings_list = []
            config = ConfigParser.ConfigParser()
            config.readfp(open(os.path.join(self.install_dir, 'cfg', 'arturo.cfg')))
            program_settings = _ProgramSettings(regexp_list = config.get('arturo', 'regexp_list').split(','),
                                               subtitle_extension_list = config.get('arturo', 'subtitle_extension_list').split(','),
                                               video_extension_list = config.get('arturo', 'video_extension_list').split(','),
                                               user_agent = config.get('arturo', 'user_agent'),
                                               log_level = config.get('arturo', 'log_level'))
            for section in config.sections():
                if section.startswith('tvseries'):
                    tvseries_settings = _TvSeriesSettings(config.get(section, 'name'),
                                                                  config.get(section, 'enabled'),
                                                                  config.get(section, 'main_tvseries_url'),
                                                                  config.get(section, 'latest_episodes_to_download'),
                                                                  os.path.expanduser(config.get(section, 'save_directory')),
                                                                  config.get(section, 'try_to_rename'),
                                                                  config.get(section, 'username'),
                                                                  config.get(section, 'password'),
                                                                  config.get(section, 'accept_pattern'),
                                                                  config.get(section, 'deny_pattern'),
                                                                  config.get(section, 'language'))
                    is_valid, error_msg = tvseries_settings.is_valid()
                    if not is_valid:
                        raise ArturoError('in [%s] %s' % (section, error_msg))
                    tvseries_settings_list.append(tvseries_settings)
            tvseries_settings_list.reverse()
            return _Settings(program_settings, tvseries_settings_list)
        except (ConfigParser.ParsingError,Exception), err:
            raise ArturoError('Configuration file error: %s' % str(err))

    def print_tvseries_settings(self):
        "This method print tv series settings"
        for tvseries_settings in self.settings.tvseries_settings_list:
            print(tvseries_settings)

    def print_program_settings(self):
        "This method print program settings"
        print(self.settings.program_settings)

    def print_order_pad(self):
        "This method print all enabled tv series"
        print('Today Sir, your order is:')
        for tvseries_settings in self.settings.tvseries_settings_list:
            if tvseries_settings.is_enabled() :
                if tvseries_settings.latest_episodes_to_download == '*':
                    print "* ALL episodes of tv series [%s]" % (tvseries_settings.name)
                else:
                    print "* %s episodes of tv series [%s]" % (tvseries_settings.latest_episodes_to_download, tvseries_settings.name)
    def serve_subtitles(self):
        "This Method calls Arturo at work."""
        #self.print_program_settings()
        #self.print_tvseries_settings()
        self.print_order_pad()
        subtitles_tool = SubtitlesTool(self.settings.program_settings)
        for tvseries_settings in self.settings.tvseries_settings_list:
            subtitles_tool.process(tvseries_settings)
        print("Sir, your subtitles are SERVED!")
        logging.info("DONE!")


class  _ProgramSettings(object):
    """This class represents program settings """
    def __init__(self, regexp_list, subtitle_extension_list, video_extension_list, user_agent, log_level):
        self.regexp_list = regexp_list
        self.subtitle_extension_list = subtitle_extension_list
        self.video_extension_list = video_extension_list
        self.user_agent = user_agent
        self.log_level = log_level

    def __str__(self):
        """Convenient class for object print"""
        return "Regular expression: %s, Subtitle extensions: %s, Video extensions %s, User agent: %s, Log level: %s" % \
            (self.regexp_list,
            self.subtitle_extension_list,
            self.video_extension_list,
            self.user_agent,
            self.log_level)


class  _TvSeriesSettings(object):
    """This class represents tv series settings """
    def __init__(self, name, enabled, main_tvseries_url, latest_episodes_to_download = '0', save_directory = '', try_to_rename = 'N', username = '', password = '', accept_pattern = '', deny_pattern = '', language = ''):
        self.name = name
        self._enabled = enabled
        self.main_tvseries_url = main_tvseries_url
        self.latest_episodes_to_download = latest_episodes_to_download
        self.save_directory = save_directory
        self.accept_pattern = accept_pattern
        self.deny_pattern = deny_pattern
        self.username = username
        self.password = password
        self.language = language
        self._try_to_rename = try_to_rename

    def is_valid(self):
        """Test if tv series settings is well configured"""
        error_message = ""
        if not re.match('^[YN]$', self._enabled):
            error_message = "enabled value must be Y or N"
        if self.name == '':
            error_message = "name value cannot be empty"
        if self.main_tvseries_url == '':
            error_message = "main_tvseries_url value cannot be empty"
        if not re.match('^[YN]$', self._try_to_rename):
            error_message = "try_to_rename value must be Y or N"
        if not re.match('^[0-9]$|^[1-9][0-9]$|^\*$', self.latest_episodes_to_download):
            error_message = "latest_episodes_to_download value must be between 0-99 or *"
        if not re.match('(((https?)://([A-Za-z0-9%\-_]+(:[A-Za-z0-9%\-_]+)?@)?([A-Za-z0-9\-]+\.)+[A-Za-z0-9]+)(:[0-9]+)?(/([A-Za-z0-9\-_\?!@#$%^&*/=\.]+[^\.\),;\|])?)?)', self.main_tvseries_url):
            error_message = "main_tvseries_url is not a valid url"
        plugin_package_name = self.get_plugin_package_name()
        try:
            getattr(__import__(plugin_package_name, globals(), locals(), ['']), 'Scraper')
        except Exception:
            error_message = "can't find plugin %s" % plugin_package_name
        return (error_message == "", error_message)

    def __str__(self):
        """Convenient class for object print"""
        return "Name: %s, Enabled: %s, Url %s, Episodes: %s, Save dir: %s, Try to rename: %s, Accept pattern: %s, Deny pattern: %s, Username: %s, Password: %s, Language: %s" % \
            (self.name,
            self.is_enabled(),
            self.main_tvseries_url,
            self.latest_episodes_to_download,
            self.save_directory,
            self.has_to_rename(),
            self.accept_pattern,
            self.deny_pattern,
            self.username,
            self.password,
            self.language)

    def has_to_rename(self):
        """Convenient method to handle _try_to_rename parameter."""
        return self._try_to_rename == 'Y'

    def is_enabled(self):
        """Convenient method to handle _enabled parameter."""
        return self._enabled == 'Y'

    def get_plugin_package_name(self):
        """Return the correct package name to use, parsing the main_tv_series_url domain."""
        parsed_url = urlparse.urlparse(self.main_tvseries_url)
        parts = parsed_url[1].split(".")
        if len(parts) == 2:
            return (parts[1]+"."+parts[0]).lower()
        elif len(parts) == 3:
            return (parts[2]+"."+parts[1]).lower()
        elif len(parts) == 4:
            return (parts[3]+"."+parts[2]+"."+parts[1]).lower()
        else:
            return ""

class SubtitlesTool(object):
    """ A tool for scrape, download, move and rename subtitles"""
    def __init__(self, program_settings):
        self.tmp_download_directory = tempfile.mkdtemp()
        self.program_settings = program_settings
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        opener.addheaders = [("User-agent", self.program_settings.user_agent)]
        urllib2.install_opener(opener)
        self.opener = opener

    def _unzip (self, zipped_file):
        """Unzip and return the name of unzipped subtitles file."""
        zip_file = zipfile.ZipFile(zipped_file, 'r')
        #Search for the first subtitles in case it contains more than one file
        file_name_to_extract = ''
        for name in zip_file.namelist():
            file_extension = os.path.splitext(name)[1]
            if (file_extension[1:].upper() in self.program_settings.subtitle_extension_list):
                file_name_to_extract = name
                break
        #Just in case zipped subtitles files are inside directory 
        splitted_file_name = file_name_to_extract.split("/")
        if len(splitted_file_name) > 1 :
            file_name_fixed = splitted_file_name[len(splitted_file_name)-1]
        else:
            file_name_fixed = file_name_to_extract
        open(os.path.join(self.tmp_download_directory, file_name_fixed), "w").write(zip_file.read(file_name_to_extract))
        zip_file.close()
        return file_name_fixed

    def scrape_urls(self, tvseries_settings):
        """ Return a list of urls that represent subtitles to download"""
        if tvseries_settings.is_enabled():
            scraped_url_list = []
            scraper_class = getattr(__import__(tvseries_settings.get_plugin_package_name(), globals(), locals(), ['']), 'Scraper')
            scraped_url_list = scraper_class(self.opener, tvseries_settings).get_subtitles_file_url_list(tvseries_settings)
            logging.info(str('[%s] scraped %d urls' % (tvseries_settings.name, len(scraped_url_list))))
            return scraped_url_list

    def download_subtitles(self, tvseries_settings, subtitles_file_url_list):
        """ Download and if necessary, extract, subtitles from the passed url_list"""
        downloaded_subtitles = []
        if tvseries_settings.is_enabled():
            start_index, end_index = _get_normalized_range_index(len(subtitles_file_url_list), tvseries_settings)
            for episode_number in range(start_index, end_index):
                #Download
                episode_url = subtitles_file_url_list[episode_number]
                resp = self.opener.open(episode_url)
                content_type = resp.info().get("Content-Type")
                try:
                    file_name = cgi.parse_header(resp.info().get("Content-Disposition"))[1]['filename']
                except Exception:
                    file_name = 'fileTemp'
                file_type = _get_downloaded_file_type(file_name, content_type, self.program_settings.subtitle_extension_list)
                #Zip
                if file_type == ZIP_FILE_TYPE:
                    open(os.path.join(self.tmp_download_directory, file_name), "wb").write(resp.read())
                    file_name_extracted = self._unzip(os.path.join(self.tmp_download_directory, file_name))
                    downloaded_subtitles.append(file_name_extracted)
                    logging.info(str('[%s] %s downloaded!' % (tvseries_settings.name, file_name_extracted)))
                #Text
                elif file_type == TEXT_FILE_TYPE:
                    open(os.path.join(self.tmp_download_directory, file_name), "w").write(resp.read())
                    downloaded_subtitles.append(file_name)
                    logging.info(str('[%s] %s downloaded!' % (tvseries_settings.name, file_name)))
                #Rar
                elif file_type == RAR_FILE_TYPE:
                    logging.info(str('[%s] %s rar file not supported yet!' % (tvseries_settings.name, file_name)))
        return downloaded_subtitles

    def move_subtitles(self, tvseries_settings, file_list):
        """ Move downloaded file_list from temporary directory to save directory"""
        if tvseries_settings.is_enabled():
            for file_name in file_list:
                try:
                    shutil.move(os.path.join(self.tmp_download_directory, file_name), tvseries_settings.save_directory)
                    logging.info(str('[%s] %s moved!' % (tvseries_settings.name, file_name)))
                except (IOError, Exception), err:
                    logging.warning(str("[%s] Problem moving %s: %s" % (tvseries_settings.name, file_name, str(err))))

    def rename_subtitles(self, tvseries_settings):
        """ Rename subtitles found in save_directory"""
        if tvseries_settings.is_enabled() and tvseries_settings.has_to_rename():
            file_info_list = _get_supported_file_info_list(tvseries_settings.save_directory,
                                                             self.program_settings.regexp_list,
                                                             self.program_settings.video_extension_list,
                                                             self.program_settings.subtitle_extension_list)
            for file_info in file_info_list:
                if file_info.is_video_type() and file_info.season_number != EMPTY_SEASON and file_info.episode_number != EMPTY_EPISODE:
                    for file_info_searching_sub in file_info_list:
                        if file_info_searching_sub.is_subtitle_type() and \
                            str(file_info.file_base) != str(file_info_searching_sub.file_base) and \
                            int(file_info_searching_sub.season_number) == int(file_info.season_number) and \
                            int(file_info_searching_sub.episode_number) == int(file_info.episode_number):
                            try:
                                os.rename(file_info_searching_sub.file_name, file_info.file_base+file_info_searching_sub.file_extension)
                                logging.info(str('[%s] %s renamed!' % (tvseries_settings.name, file_info_searching_sub.file_name)))
                            except OSError:
                                pass
                            try:
                                os.remove(file_info_searching_sub.file_name)
                                logging.info(str('[%s] %s removed!' % (tvseries_settings.name, file_info_searching_sub.file_name)))
                            except OSError:
                                pass
                            break

    def process (self, tvseries_settings):
        """ Run all operations in one single batch"""
        if tvseries_settings.is_enabled():
            print('Processing tv series: %s' % tvseries_settings.name)
            scraped_url_list = self.scrape_urls(tvseries_settings)
            downloaded_subtitles_list = self.download_subtitles(tvseries_settings, scraped_url_list)
            self.move_subtitles(tvseries_settings, downloaded_subtitles_list)
            self.rename_subtitles(tvseries_settings)

    def __del__(self):
        shutil.rmtree(self.tmp_download_directory)

class _Settings(object):
    """Class used to store program settings"""
    def __init__(self, program_settings, tvseries_settings_list):
        self.program_settings = program_settings
        self.tvseries_settings_list = tvseries_settings_list


class _FileInfo(object):
    """Convenient wrapper used to store infos about supported file."""
    def __init__(self, season_number, episode_number, file_name, file_base, file_extension, file_type):
        self.season_number = season_number
        self.episode_number = episode_number
        self.file_name = file_name
        self.file_base = file_base
        self.file_extension = file_extension
        self.file_type = file_type

    def is_video_type(self):
        """Check if file is a video."""
        return self.file_type == VIDEO_FILE_TYPE

    def is_subtitle_type(self):
        """Check if file is a subtitle."""
        return self.file_type == SUBTITLE_FILE_TYPE


class ArturoError(Exception):
    """Base class for Arturo exceptions."""
    pass


def _get_supported_file_info_list(directory, regexp_list, video_extension_list, subtitle_extension_list):
    """Return a list of file_info of supported video\subtitles files found inside directory."""
    file_info_list = []
    for file_name in os.listdir(directory):
        is_supported = False
        if os.path.isfile(os.path.join(directory, file_name)):
            file_base, file_extension = os.path.splitext(file_name)
            file_type, season_number, episode_number = '', EMPTY_SEASON, EMPTY_EPISODE
            if file_extension != '' and (file_extension[1:].upper() in video_extension_list):
                file_type = VIDEO_FILE_TYPE
                is_supported = True
            if file_extension != '' and (file_extension[1:].upper() in subtitle_extension_list):
                file_type = SUBTITLE_FILE_TYPE
                is_supported = True
            if is_supported:
                for re_reg_pattern in regexp_list:
                    match_file = re.compile(re_reg_pattern).search(file_name)
                    if match_file:
                        season_number = match_file.group(1)
                        episode_number = match_file.group(2)
                        break
                file_info_list.append(_FileInfo(season_number, episode_number, os.path.join(directory, file_name), os.path.join(directory, file_base), file_extension, file_type))
    return file_info_list

def _get_normalized_range_index(subtitle_url_list_length, tvseries_settings):
    "Return the correct indexes used to scan subtitle_url_list."
    if subtitle_url_list_length == 0:
        logging.info(str('[%s] No episodes found!' % (tvseries_settings.name)))
    if tvseries_settings.latest_episodes_to_download == '0':
        logging.info(str('[%s] No episodes to download!' % (tvseries_settings.name)))
    if tvseries_settings.latest_episodes_to_download == '*':
        start_index_episode = 0
    else:
        start_index_episode = subtitle_url_list_length -int(tvseries_settings.latest_episodes_to_download)
    if start_index_episode < 0:
        start_index_episode = 0
    end_index_episode = subtitle_url_list_length
    return (start_index_episode, end_index_episode)

def _get_downloaded_file_type(file_name, content_type, subtitle_extension_list):
    """Return the type of downloaded file by checking file name and content type."""
    file_extension = os.path.splitext(file_name)[1]
    file_type = UNKNOWN_FILE_TYPE
    if file_extension[1:].upper() == 'ZIP' or content_type in ('application/zip', 'application/x-zip-compressed'):
        file_type = ZIP_FILE_TYPE
    elif file_extension[1:].upper() == 'RAR' or content_type == 'application/x-rar-compressed':
        file_type = RAR_FILE_TYPE
    elif file_extension[1:].upper() in subtitle_extension_list or content_type == 'text/plain':
        file_type = TEXT_FILE_TYPE
    return file_type

def main(argv = None):
    """The main function calls Arturo at work"""
    if argv is None:
        argv = sys.argv
    try:       
        install_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        arturo = Arturo(install_dir)
        arturo.serve_subtitles()
    except Exception, err:
        print("ERROR! (Check log)")
        logging.error(err)
        return 1
if __name__ == "__main__":
    sys.exit(main())
