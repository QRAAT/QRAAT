USE qraat; 
UPDATE processing_cursor SET value=(SELECT min(ID) FROM est) WHERE name='estscore';
UPDATE processing_cursor SET value=0 WHERE name IN ("position", "track_posj");
