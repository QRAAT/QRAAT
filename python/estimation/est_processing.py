import est_data
import os

server_dir = '/rmg_server'
sitelist = server_dir + '/rmg_site_list'
det_dir = server_dir + '/det_files/'
est_dir = server_dir + '/est_files/'

def process_det_files(det_dirname, est_dirname):
    print "Processing " + det_dirname
    est = est_data.est_data()
    est.read_dir(det_dirname)
    if est.num_tags > 0:
        est.write_est(est_dirname)

def find_latest_dir(est_rmg_site_dir):
    try:
        with open(est_rmg_site_dir + 'last_directory_processed') as f:
            latest = []
            latest.append(f.read(4))
            for j in range(4):
                latest.append(f.read(2))
    except IOError:
        latest = []
        dir_str = ''
        for j in range(5):
            dirlist = sorted(os.listdir(est_rmg_site_dir + dir_str))
            count = -1
            while (count >= -len(dirlist) and not os.path.isdir(est_rmg_site_dir + dir_str + dirlist[count])):
                count += -1
            if count >= -len(dirlist):
                latest.append(dirlist[count])
                dir_str += dirlist[count] + '/'
            else:
                for k in range(5-j):
                    latest.append('')
                break
        #latest, found_dir = search_for_dirs(est_rmg_site_dir, ['', '', '', '', ''], 0, [])
    return latest

def write_latest_dir(dirname, latest):
    with open(dirname + 'last_directory_processed','w') as f:
        for j in latest:
            f.write(j)

def read_rmg_list(filename):
#TODO
    return ['rmg_site_test']

def search_for_dirs(rmg_site_dir_str, latest, depth, found_dir):

    dir_str = ''
    for j in range(depth):
        dir_str += latest[j] + '/'
    if depth == 5:
        found_dir.append(dir_str)
    elif depth < 5:
        if not latest[depth] == '':
            latest, found_dir = search_for_dirs(rmg_site_dir_str, latest, depth+1, found_dir)
        dirlist = sorted(os.listdir(rmg_site_dir_str + dir_str))
        for j in dirlist:
            if j > latest[depth] and os.path.isdir(rmg_site_dir_str + dir_str + j):
                latest[depth] = j
                for k in range(depth+1,5):
                    latest[k] = ''
                latest, found_dir = search_for_dirs(rmg_site_dir_str, latest, depth + 1, found_dir)
    return latest, found_dir

if __name__=="__main__":

    rmg_list = read_rmg_list(sitelist)
    for rmg_site in rmg_list:
        det_rmg_dir = det_dir + rmg_site + '/'
        est_rmg_dir = est_dir + rmg_site + '/'
        latest, found_dir = search_for_dirs(det_rmg_dir, find_latest_dir(est_rmg_dir), 0, [])
        for det_dir_process in found_dir[1:]:
            process_det_files(det_rmg_dir + det_dir_process, est_rmg_dir + det_dir_process)
        write_latest_dir(est_rmg_dir, latest)
        
