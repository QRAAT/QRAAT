#!/usr/bin/env python2
# fix-gropus.py -- QRAAT metadata is dumped without Django group/user 
# data. The code (as written) assumes the existence of groups corresponding
# to qraat.auth_project_{viewer,collaborator}. This script removes whatever
# groups are there and uses the `qraat` tables to create new ones. 

import qraat, qraat.srv
import time, os, sys, commands
import MySQLdb as mdb
import re

try: 
  start = time.time()
  print "create-groups: start time:", time.asctime(time.localtime(start))

  db_con = qraat.srv.util.get_db('reader')  
  
  # Get viewer and collaborator group IDs for each projectID. 
  viewers = qraat.csv.csv(db_con=db_con, db_table='auth_project_viewer')
  collaborators = qraat.csv.csv(db_con=db_con, db_table='auth_project_collaborator')
  projects = qraat.csv.csv(db_con=db_con, db_table='project')
  projectIDs = []
  for project in projects:
    projectIDs.append(int(project.ID))
  
  print "--- auth_project_view ------------"
  print viewers
  print
  print "--- auth_project_collaborator ----"
  print collaborators
  print

  db_con.close()
  db_con = qraat.srv.util.get_db('admin')
  cur = db_con.cursor()

  # Resolve projects users have access to and what they can do.  
  cur.execute('''SELECT user_id, name 
                   FROM auth_group 
                   JOIN auth_user_groups 
                     ON auth_group.id = auth_user_groups.group_id''')

  proj_view_users = {}
  proj_collaborate_users = {}
  group_name_regex = re.compile("^([0-9]+)_([a-zA-z]+)$")
  for (user_id, group_name) in cur.fetchall(): 
    (proj_id, proj_perm) = group_name_regex.match(group_name).groups()
    proj_id = int(proj_id); user_id = int(user_id)
    if proj_id in projectIDs:
      if proj_perm == 'viewers' or proj_perm == 'viewer': 
        if proj_view_users.get(proj_id):
          proj_view_users[proj_id].append(user_id)
        else: 
          proj_view_users[proj_id] = [user_id]
      if proj_perm == 'collaborators' or proj_perm == 'collaborator': 
        if proj_collaborate_users.get(proj_id):
          proj_collaborate_users[proj_id].append(user_id)
        else: 
          proj_collaborate_users[proj_id] = [user_id]
 
  print "--- Users in groups --------------"
  print "view:       ", proj_view_users
  print "collaborate:", proj_collaborate_users
  print 
  
  # Create an index for permissions. 
  permission_id = {}
  cur.execute('SELECT id, codename FROM auth_permission') 
  for (id, codename) in cur.fetchall():
    permission_id[codename] = id
  
  # Delete whatever is in the tables. 
  cur.execute('DELETE FROM auth_user_groups')
  cur.execute('DELETE FROM auth_group_permissions')
  cur.execute('DELETE FROM auth_group')

  # Create new group, set permissions, and add users to gruop. 
  for viewer in viewers: 
    cur.execute('INSERT INTO auth_group (id, name) VALUE (%s, %s)',
      (viewer.groupID, '%d_viewers' % viewer.projectID))
    
    cur.execute('''INSERT INTO auth_group_permissions 
                      (group_id, permission_id) VALUE (%s, %s)''', 
      (viewer.groupID, permission_id['can_view']))
    
    if proj_view_users.get(viewer.projectID): 
      for user_id in proj_view_users[viewer.projectID]: 
        cur.execute('INSERT INTO auth_user_groups (user_id, group_id) VALUE (%s, %s)', 
           (user_id, viewer.groupID))

  for collaborator in collaborators: 
    cur.execute('INSERT INTO auth_group (id, name) VALUE (%s, %s)',
      (collaborator.groupID, '%d_collaborators' % collaborator.projectID))
    
    cur.executemany('''INSERT INTO auth_group_permissions 
                       (group_id, permission_id) VALUE (%s, %s)''', 
      [(collaborator.groupID, permission_id['can_view']),
       (collaborator.groupID, permission_id['can_change']),
       (collaborator.groupID, permission_id['can_hide'])])
    
    if proj_collaborate_users.get(collaborator.projectID): 
      for user_id in proj_collaborate_users[collaborator.projectID]: 
        cur.execute('INSERT INTO auth_user_groups (user_id, group_id) VALUE (%s, %s)', 
           (user_id, collaborator.groupID))

  cur.execute('COMMIT')

except qraat.error.QraatError, e:
  print >>sys.stderr, "create-groups: error: %s." % e

finally: 
  print "create-groups: finished in %.2f seconds." % (time.time() - start)
