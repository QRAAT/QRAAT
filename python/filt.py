# filt.py - High level API calls for various filters. These return table IDs. 
# TODO better name 

def est_band(db_con, tx_id, t_start, t_end):
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM est
                  WHERE txID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f 
                    AND band3 < 150 
                    AND band10 < 900''' % (tx_id, t_start, t_end))
  return [ int(row[0]) for row in cur.fetchall() ]

def est_nofilter(db_con, tx_id, t_start, t_end):
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM est
                  WHERE txID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f''' % (tx_id, t_start, t_end))
  return [ int(row[0]) for row in cur.fetchall() ]
  

def pos_nofilter(db_con, tx_id, t_start, t_end):
  cur = db_con.cursor()
  cur.execute('''SELECT ID 
                   FROM Position
                  WHERE txID=%d
                    AND timestamp >= %f 
                    AND timestamp <= %f''' % (tx_id, t_start, t_end))
  return [ int(row[0]) for row in cur.fetchall() ]
  
