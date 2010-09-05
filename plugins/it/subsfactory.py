"""Scraping from www.subsfactory.it"""
import re
import logging

class Scraper:
    
    def __init__(self,opener,tvseries_settings):
        missing_parameter = self._get_missing_parameters(tvseries_settings)
        if missing_parameter != '':
            raise Exception("[%s] Plugin %s requires : %s " % (tvseries_settings.name, tvseries_settings.get_plugin_package_name(), missing_parameter))
        self.opener=opener
    
    def _get_missing_parameters(self, tvseries_settings):
        return ""
    
    def get_subtitles_file_url_list(self,tvseries_settings):
        link_found=[]
        link_found_after_accept=[]
        link_found_after_deny=[]
        resp= self.opener.open(tvseries_settings.main_tvseries_url)
        data = resp.read()
        link_finder_main=re.compile('<td class="modulecell" width="\*"><a href="(.*?)"',re.DOTALL|re.IGNORECASE)
        link_found_main=link_finder_main.findall(data)
        for link in link_found_main:
            resp= self.opener.open('http://www.subsfactory.it/'+link)            
            data = resp.read()          
            link_finder_detail=re.compile('op=download_file(.*?)" title="Scarica file"><img',re.DOTALL|re.IGNORECASE)
            link_found.append('http://www.subsfactory.it/index.php?ind=downloads&op=download_file'+link_finder_detail.findall(data)[0])
        #accept_pattern    
        for link in link_found:
            if tvseries_settings.accept_pattern.strip()!='' and not(re.search(tvseries_settings.accept_pattern,link)):
                pass
            else:
                link_found_after_accept.append(link)
        #deny_pattern
        for link in link_found_after_accept:            
            if tvseries_settings.deny_pattern.strip()!='' and re.search(tvseries_settings.deny_pattern,link):
                pass
            else:
                link_found_after_deny.append(link)            
        logging.debug(str("[%s] Link found : %s" % (tvseries_settings.name,link_found_after_deny)))
        return link_found_after_deny
