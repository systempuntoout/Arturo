"""Scraping from www.italiansubs.net"""
import re
import logging


class Scraper(object):
    
    def __init__(self,opener,tvseries_settings):
        missing_parameter = self._get_missing_parameters(tvseries_settings)
        if missing_parameter != '':
            raise Exception("[%s] Plugin %s requires : %s " % (tvseries_settings.name, tvseries_settings.get_plugin_package_name(), missing_parameter))
        opener.open('http://www.italiansubs.net/index.php?option=com_smf&Itemid=26&action=login2&user='+tvseries_settings.username+'&passwrd='+tvseries_settings.password+'&cookielength=-1&hash_passwrd=')
        self.opener=opener
    
    def _get_missing_parameters(self, tvseries_settings):
        if (tvseries_settings.username == '' or tvseries_settings.password == ''):
            return "username, password"
        else:
            return ""
    
    def get_subtitles_file_url_list(self,tvseries_settings):
        link_found=[]
        link_found_filtered=[]
        resp= self.opener.open(tvseries_settings.main_tvseries_url)
        data = resp.read()
        link_finder=re.compile('<dl><a href="(.*?)"',re.DOTALL|re.IGNORECASE)
        link_found=link_finder.findall(data)
        for link in link_found:
            if not(tvseries_settings.deny_pattern.strip()!='' and re.search(tvseries_settings.deny_pattern,link)):link_found_filtered.append(link)            
        logging.debug(str("[%s] Link found : %s" % (tvseries_settings.name,link_found_filtered)))
        return link_found_filtered

