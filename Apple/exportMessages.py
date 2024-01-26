#!/bin/env python
####################################################################################################
# exportMessages.py
# by (github.com/t-truong)
# This script exports messages on an iPhone to a text file
#
# Dependencies are {python >= 2.7, pandas}
# argv[1]= path to directory containing {chat.db} and {Attachments}
# argv[2]= phone number, only numbers are parsed and characters are ignored
#
# Data is pulled from {~/Library/Messages/chat.db} and {~/Library/Messages/Attachments} on MacOS.
# The script only requires the database file and attachments databse to work; as long as the Python
# version is met, the script will run on MacOS or Linux.
#
# Credits: https://github.com/PeterKaminski09/baskup/blob/master/baskup.sh
#          https://github.com/my-other-github-account/imessage_tools/blob/master/imessage_tools.py
####################################################################################################





#IMPORTS============================================================================================
#native---------------------------------------------------------------------------------------------
import os
import sys
import shutil

import sqlite3
import datetime as dt





#external-------------------------------------------------------------------------------------------
import pandas as pd
pd.options.mode.chained_assignment= None





#GLOBALS============================================================================================
DB_PATH = sys.argv[1]
PHONE_NUMBER= sys.argv[2]





#FUNCTIONS==========================================================================================
def parseAttributedBody(attrbody):
    """Parse {attributedBody} column in {message} table from {chat.db}

    If {text} column is empty, check {attributedBody} column for text. Apple decided on some
    clusterfuck implementation so this is sometimes necessary.

    Parameters
    ----------
    attrbody: bytes
              | Bytes from {attributedBody} column decodeable to utf-8

    Returns
    -------
    attrbody: str
              | Parsed {attributedBody} column
    """
    attrbody= attrbody.decode("utf-8", errors= "replace")
    if "NSNumber" in attrbody:
        attrbody= attrbody.split("NSNumber")[0]
        if "NSString" in attrbody:
            attrbody= attrbody.split("NSString")[1]
            if "NSDictionary" in attrbody:
                attrbody= attrbody.split("NSDictionary")[0]
                attrbody= attrbody[6:-12]
    return attrbody


def getMessages(directorypath, phone):
    """Get text messages and attachments for a phone number

    Data is pulled from {chat.db} and {Attachments} database

    Parameters
    ----------
    directorypath: str
                   | Path to directory containing {chat.db} and {Attachments}

    phone        : str
                   | Phone number to get messages to and from
                   | Raw user input is accepted, function will sanitize by parsing numbers and ignoring characters

    Returns
    -------
    texts   : list[str]
              | Date sorted (ascending) list of texts and file names formatted correctly for writing to file
              | Each element in the list represents a message and is newline terminated

    Messages: pandas.DataFrame
              | DataFrame containing processed information on the conversation
              | Attachments are shown as full paths to where they can be copied into archive
    """
    #Initialization---------------------------------------------------------------------------------
    con              = sqlite3.connect(f"{directorypath.rstrip('/')}/chat.db")
    DF_Chat          = pd.read_sql_query("SELECT * FROM chat", con)                    #contains phone number
    DF_MessageJoin   = pd.read_sql_query("SELECT * FROM chat_handle_join", con)        #contains correlation between phone number and messages
    DF_Message       = pd.read_sql_query("SELECT * FROM message", con)                 #contains text from messages
    DF_AttachmentJoin= pd.read_sql_query("SELECT * FROM message_attachment_join", con) #contains correlation between messages and attachments
    DF_Attachment    = pd.read_sql_query("SELECT * FROM attachment", con)              #contains attachments
    SanitizedNumber= ''.join(filter(str.isdigit, phone))
    #Phone Number Filters---------------------------------------------------------------------------
    guid_filter= DF_Chat["guid"].str.contains(SanitizedNumber)                                 #get filter in {DF_Chat} where {guid} contains specified phone number
    chatid     = int(DF_Chat["ROWID"][guid_filter].iloc[0])                                    #get {ROWID} in {DF_Chat}, this integer corresponds to {chat_id} in {DF_MessageJoin}
    handleid   = int(DF_MessageJoin["handle_id"][DF_MessageJoin["chat_id"] == chatid].iloc[0]) #use {ROWID} from {DF_Chat} to get {handle_id} in {DF_MessageJoin}

    handleid_filter= DF_Message["handle_id"] == handleid #{handleid} is used to correspond text in {DF_Message} to recipient
    #Get Messages-----------------------------------------------------------------------------------
    selection  = ["ROWID", "cache_has_attachments", "is_from_me", "date", "text", "attributedBody"]
    Messages= DF_Message[handleid_filter][selection]
    #convert timestamp from nanoseconds since 2001/01/01 to human readable and also sort
    epoch= dt.datetime(2001, 1, 1).timestamp()
    Messages["date"]= Messages["date"]/1000000000 + epoch
    Messages.sort_values("date", inplace= True)
    Messages["date"]= Messages["date"].map(dt.datetime.fromtimestamp).astype(str)
    #process between {text, attributedBody}
    processed= [None]*len(Messages)
    for i, text in enumerate(Messages["text"]):
        if text is None or len(text) == 0:
            processed[i]= parseAttributedBody(Messages.iloc[i]["attributedBody"])
        else:
            processed[i]= text
    Messages["processed"]= processed
    #Attachment Filters-----------------------------------------------------------------------------
    has_attachment_filter= Messages["cache_has_attachments"] == 1                    #filter for attachments
    messageids           = Messages["ROWID"][has_attachment_filter]                  #get {ROWID} in {DF_Message} which corresponds to {message_id} in {DF_AttachmentJoin}
    messageids_filter    = DF_AttachmentJoin["message_id"].isin(messageids)             #filter for rows where {message_id} is in {ROWID} of {DF_Message}
    attachmentids        = DF_AttachmentJoin["attachment_id"][messageids_filter]        #get {attachment_id} which corresponds to {ROWID} in {DF_Attachment}
    attachmentids_filter = DF_Attachment["ROWID"].isin(attachmentids)                   #filter for rows where {ROWID} of {DF_Attachment} is in {attachment_id}
    #Get Attachments--------------------------------------------------------------------------------
    #one time function reading in one {ROWID} from {DF_Message} and returning a string containing paths to attachments
    pd.options.display.max_colwidth= 999 #required to correctly get long paths
    def linkAttachments(messageid):
        attachmentids  = DF_AttachmentJoin["attachment_id"][DF_AttachmentJoin["message_id"] == messageid]
        attachmentpaths= DF_Attachment["filename"][DF_Attachment["ROWID"].isin(attachmentids)]
        return attachmentpaths.to_string(header= False, index= False).replace("~/Library/Messages", directorypath.rstrip('/'))
    Messages["links"]= None
    Messages["links"][has_attachment_filter]= Messages["ROWID"][has_attachment_filter].map(linkAttachments)
    #Format for Writing to .txt---------------------------------------------------------------------
    texts= Messages[["is_from_me", "date", "processed"]].to_string(header= False, index= False).split('\n') #get row separated list of strings
    texts= [' '.join(e.split()) for e in texts]                                                             #clean up

    num_attachments  = len(DF_Attachment[attachmentids_filter])
    num_prefix_digits= len(str(num_attachments))
    incr_attachments = 1
    Messages["basename"]= None
    for i, line in enumerate(texts):
        if line[0] == '0': metadata= f"[Other @ {texts[i][2:28]}] "
        else             : metadata= f"[Me    @ {texts[i][2:28]}] "

        is_attachment= bool(int(Messages["cache_has_attachments"].iloc[i]))
        if is_attachment: 
            paths            = Messages["links"].iloc[i].split('\n')
            filenames        = [f"{incr_attachments + k:0{num_prefix_digits}d}_{os.path.basename(p)}" for k, p in enumerate(paths)]
            incr_attachments+= len(paths)
            content= r"\n".join(filenames)
            Messages["basename"].iloc[i]= content
        else:
            content= f"{texts[i][29:]}"
        texts[i]= metadata + content + '\n'
    Messages["final"]= texts
    return texts, Messages





#MAIN===============================================================================================
if __name__ == "__main__":
    #Initialization---------------------------------------------------------------------------------
    SanitizedNumber= ''.join(filter(str.isdigit, PHONE_NUMBER))
    if os.path.exists(SanitizedNumber): shutil.rmtree(SanitizedNumber, ignore_errors= True)
    os.mkdir(SanitizedNumber)
    #Export Messages (texts and link to attachments) to .txt File-----------------------------------
    Texts, Messages= getMessages(DB_PATH, PHONE_NUMBER)
    with open(f"./{SanitizedNumber}/messages.txt", 'w') as f: f.writelines(Texts)
    #Copy Attachments from Database to Archive------------------------------------------------------
    SourcePaths_Attachment= Messages["links"][~Messages["links"].isna()].to_string(header= False, index= False).split('\n')
    SourcePaths_Attachment= [e.split(r"\n") for e in SourcePaths_Attachment]
    SourcePaths_Attachment= [e for sublist in SourcePaths_Attachment for e in sublist]
    SourcePaths_Attachment= [e.strip() for e in SourcePaths_Attachment]
    Basename_Attachment= Messages["basename"][~Messages["basename"].isna()].to_string(header= False, index= False).split('\n')
    Basename_Attachment= [''.join(e.split()).replace(r"\n", ' ') for e in Basename_Attachment]
    Basename_Attachment= ' '.join(Basename_Attachment).replace(r"\n", ' ')
    Basename_Attachment= Basename_Attachment.split(' ')

    if not os.path.exists(f"./{SanitizedNumber}/attachments"): os.mkdir(f"./{SanitizedNumber}/attachments")
    for sourcepath, basename in zip(SourcePaths_Attachment, Basename_Attachment):
        shutil.copy2(sourcepath, f"./{SanitizedNumber}/attachments/{basename}")





####################################################################################################
# exportMessages.py
# by (github.com/t-truong)
# This script exports messages on an iPhone to a text file
####################################################################################################
