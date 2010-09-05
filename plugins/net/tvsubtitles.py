"""Scraping from www.tvsubtitles.net"""
import re
import logging


class Scraper:

    def __init__(self,opener, tvseries_settings):
        missing_parameter = self._get_missing_parameters(tvseries_settings)
        if missing_parameter != '':
            raise Exception("[%s] Plugin %s requires : %s " % (tvseries_settings.name, tvseries_settings.get_plugin_package_name(), missing_parameter))
        self.opener=opener
    
    def _get_missing_parameters(self, tvseries_settings):
        if (tvseries_settings.language == ''):
            return "language"
        else:
            return ""
    
    def get_subtitles_file_url_list(self,tvseries_settings):
        link_found=[]
        resp= self.opener.open(tvseries_settings.main_tvseries_url)
        data = resp.read()
        link_finder_main=re.compile('(subtitle|episode)-([0-9]+)(\-'+tvseries_settings.language+')?.html"><img src="images/flags/'+tvseries_settings.language+'.gif"',re.DOTALL|re.IGNORECASE)
        link_found_main=link_finder_main.findall(data)
        link_found_main.reverse()
        for link in link_found_main:
            if link[0]=='subtitle':
                link_found.append('http://www.tvsubtitles.net/download-'+link[1]+'.html')
            else:
                resp= self.opener.open('http://www.tvsubtitles.net/episode-'+link[1]+'-'+tvseries_settings.language+'.html')
                data = resp.read()
                link_finder=re.compile('subtitle-([0-9]+).html"(.*?)hspace=4>(.*?)</h5>',re.DOTALL|re.IGNORECASE)
                link_found_detail=link_finder.findall(data)
                link_found_after_accept = []
                #accept_pattern
                for link in link_found_detail:
                    if tvseries_settings.accept_pattern.strip()!='' and not(re.search(tvseries_settings.accept_pattern,link[2])):
                        pass
                    else:
                        link_found_after_accept.append(link)
                #deny_pattern
                for link in link_found_after_accept:
                    if tvseries_settings.deny_pattern.strip()!='' and re.search(tvseries_settings.deny_pattern,link[2]):
                        pass
                    else:
                        link_found.append('http://www.tvsubtitles.net/download-'+link[0]+'.html')
        logging.debug(str("[%s] Link found : %s" % (tvseries_settings.name,link_found)))
        return link_found

