Our doctor --fix adds TXT records like `fontlab.help._report._dmarc` > `v=DMARC1;` etc. 

The content field of TXT records must be in quotation marks. Cloudflare may add quotation marks on your behalf, which will not affect how the record works.

`doctor --fix` must create appropriate "dmarc acceptance" records in quotes, and it also must fix existing records that are malformed this way