import struct
import numpy as np

class antenna_pattern:

    def __init__(self,pat_filename):
        self.filename = pat_filename
        if pat_filename[-4:] == '.pat':
            with open(pat_filename) as pfile:
                (self.num_ch,) = struct.unpack('i',pfile.read(4))
                (self.num_angles,) = struct.unpack('i',pfile.read(4))
                self.pat = np.zeros((self.num_angles,self.num_ch),np.complex)
                self.angles = np.zeros((self.num_angles,),float)
                for j in range(self.num_angles):
                    self.angles[j] = struct.unpack('f',pfile.read(4))[0]
                    for k in range(self.num_ch):
                        (real_part,) = struct.unpack('f',pfile.read(4))
                        (imag_part,) = struct.unpack('f',pfile.read(4))
                        self.pat[j,k] = np.complex(real_part,imag_part)

    def likelihood_estimation(self, sig):
        result = np.zeros((self.num_angles,))
        for j in range(self.num_angles):
            p = self.pat[j,:][np.newaxis,:]
            interior = np.linalg.inv(np.dot(p.conj().transpose(),p))
            result[j] = np.abs(np.dot(sig,np.dot(interior,sig.conj().transpose())))
        return (result, self.angles[np.argmin(result)])

    def bearing_estimation(self,sig):
        (result, estimate) = self.likelihood_estimation(sig)
        return estimate

    def write_pat(self, pat_filename):
        if pat_filename[-4:] == '.pat':
            with open(pat_filename,'w') as pfile:
                pfile.write(struct.pack('i',self.num_ch))
                pfile.write(struct.pack('i',self.num_angles))
                for j in range(self.num_angles):
                    pfile.write(struct.pack('f',self.angles[j]))
                    for k in range(self.num_ch):
                        pfile.write(struct.pack('f',self.pat[j,k].real))
                        pfile.write(struct.pack('f',self.pat[j,k].imag))

if __name__ == "__main__":

    pat = antenna_pattern('/mnt/Media/RMG/Quail_Ridge/test20121106/site2_cal_utm.pat')

    import rmg.est_dict
    ed = rmg.est_dict.est_dict('/mnt/Media/RMG/Quail_Ridge/test20121106/est_files/site_2/middle_flashlight_-20121106224348-20121107012347.est')
    bw10 = np.array(ed[ed.tags()[0]].f_bw10)
    good_indexes = bw10 < 1000
    f_sigs = np.array(ed[ed.tags()[0]].f_sig)[good_indexes,:]
    print f_sigs.shape
    est_bearings = np.zeros((f_sigs.shape[0],))
    for j in range(f_sigs.shape[0]):
        est_bearings[j] = pat.bearing_estimation(f_sigs[j,:][np.newaxis,:])

    #est_bearings = pat.likelihood_estimation(pat.pat[150,:][np.newaxis,:])

    import matplotlib.pyplot as pp
    pp.plot(est_bearings,'.')
    pp.show()
