# import libaries including tf 14
# import tensorflow as tf
# import numpy as np
import sys
# import time

class sec2sec(object):
	def __init__(self,
				trainSize,
				batchSize,
				sequenceXLength,
				sequenceYLength,
				vocabXSize,
				vocabYSize,
				checkPointPath,
				epochs,
				embeddedDim,
				methodName,
				numLayers,
				lr=0.0001):
		print("started")
		self.trainSize=trainXCount
		self.batchSize=batchSize
		self.sequenceXLength=inputLength
		self.sequenceYLength=labelLength
		self.checkPointPath = checkPointPath
		self.epochs=epochs,
		self.methodName=methodName
		sys.stdout.write("Starting the graph...")
		#Added during debugging
		setattr(tf.nn.rnn_cell.BasicLSTMCell, '__deepcopy__', lambda self, _: self)
		setattr(tf.nn.rnn_cell.MultiRNNCell, '__deepcopy__', lambda self, _: self)
		def __graph__():
			tf.reset_default_graph()

			self.inputEnc = [ tf.placeholder(shape=[None,],dtype=tf.init64, name='ie_{}'.format(t)) for t in range(sequenceXLength)]
			self.labels = [tf.placeholder(shape =[None,],dtype=tf.init64,name="ie_{}".format(t)) for t in range(sequenceYLength)]
			self.inputDec = [ tf.zeros_like(self.enc_ip[0], dtype=tf.int64, name='GO') ] + self.labels[:-1]
			self.probalityKeep = tf.placeholder(tf.float32)

			basicLSTM=tf.contrib.rnn.DropoutWrapper(tf.contrib.rnn.BasicLSTMCell(embeddedDim),output_keep_prob=self.probalityKeep)
			stackedLSTM=tf.contrib.rnn.MultiRNNCell([basicLSTM]*numLayers,state_is_tuple = True)

			with tf.variable_scope('decoder') as scope:
				self.decodeOutput,self.decodeStates = tf.contrib.legacy_seq2seq.embedding_rnn_seq2seq(self.inputEnc,self.inputDec,
					stackedLSTM, vocabXSize,vocabYSize,embeddedDim,feed_previous=True)
			lossWeights= [tf.ones_like(label, dtype=tf.float32) for label in self.labels]

			#Loss function:
			self.loss =tf.contrib.legacy_seq2seq.sequence_loss(self.decodeOutput,self.labels,lossWeights,vocabYSize)
			tf.summary.scalar("loss",self.loss)
			# !!! could be removed  for better accuracy
			globalStep= tf.Variable(0,name='global_step',trainable=False)

			self.trainFit= tf.contrib.layers.optimize_loss(self.loss,global_step=globalStep,optimizer='Adam',learning_rate = lr,clip_gradient = 2.)
		__graph__()	
		sys.stdout.write('</log>')
	def getFeed(self, X, Y, keep_prob):
		feedDictionary = {self.enc_ip[t]: X[t] for t in range(self.xseq_len)}
		feedDictionary.update({self.labels_fwd[t]: Y[t] for t in range(self.yseq_len)})
		feedDictionary[self.keep_prob] = keep_prob # dropout prob
        # print("Feed dict: {}".format(feedDictionary))
		return feedDictionary

    # run one batch for training
	def trainBatch(self, sess, trainBatchGen):
        # get batches
		batchX, batchY = trainBatchGen.__next__()
#!!!! Important play with the keep probality to see changes
		feedDictionary = self.getFeed(batchX, batchY, keep_prob=0.5)
		summary,_, lossEval = sess.run([self.train_op, self.loss], feedDictionary)
		return summary,lossEval

	def evalStep(self, sess, evalBatchGen):
        # get batches
		batchX, batchY = evalBatchGen.__next__()
		feedDictionary = self.getFeed(batchX, batchY, keep_prob=1.)
		lossEval, decodeOpEval = sess.run([self.loss, self.decode_outputs_test_fwd], feedDictionary)
		decodeOpEval = np.array(decodeOpEval).transpose([1,0,2])
		return lossEval, decodeOpEval, batchX, batchY

    # evaluate 'numBatches' batches
	def evalBatch(self, sess, evalBatchGen, numBatches):
		losses = []
		for i in range(numBatches):
			lossEval, decodeOpEval, batchX, batchY = self.evalStep(sess, evalBatchGen)
			losses.append(lossEval)
		return np.mean(losses)
	def train(self, train_set, valid_set, sess=None ):
        
        # we need to save the model periodically
		saver = tf.train.Saver()
		if not sess:
			sess = tf.Session()

			merged = tf.summary.merge_all()
			sess.run(tf.global_variables_initializer())

		sys.stdout.write('\nTraining started ..\n')


		inputSize = self.trainSize[0]
		batchSize = self.batchSize[0]
		numSteps = inputSize//batchSize
		print(numSteps)
		previousValLoss = 1000000
		previousValLosses = list()
		patience = 100
		valLossEvaluationStep = 100
		for i in range(self.epochs):
			if i == 0:
				epoch_start_time = time.time()
			for j in range(numSteps):
				if j == 0:
					steps_start_time = time.time()
				try:
                    summary, _ = self.trainBatch(sess, merged, train_set)
                    summary_writer.add_summary(summary)
				except KeyboardInterrupt: # this will most definitely happen, so handle it
					print('Interrupted by user at iteration {}'.format(i))
					self.session = sess
				if j and j % valLossEvaluationStep == 0:
					val_loss = self.evalBatch(sess, valid_set, 8)
                    # writer.add_summary(summary)
					steps_eval_time = time.time() - steps_start_time
					print('val loss : {0:.6f} in {1:.2f} secs Epoch: {2}/{3} step/epoch'.format(val_loss,
                                                                                                steps_eval_time, j, i))
					if i > 0 and val_loss > previousValLoss:
						saver.save(sess, self.checkPointPath + self.methodName + '.ckpt', global_step=i)
						previousValLoss.append(val_loss)
						if len(previousValLoss) >= patience:
							print("Early stopping at {0}/{1} with validation loss: {2}".format(j, i, val_loss))
							return sess
					if val_loss < previousValLoss and previousValLoss is not None:
						previousValLoss = list()
					previousValLoss = val_loss
					steps_start_time = time.time()

            # save model to disk
			saver.save(sess, self.checkPointPath + self.methodName + '.ckpt', global_step=i)
            # evaluate to get validation loss
			val_loss = self.evalBatch(sess, valid_set, 8)  # TODO : and this
			epoch_eval_time = time.time() - epoch_start_time
			print('val loss : {0:.6f} in {1:.2f} secs Epoch: {2} epoch'.format(val_loss, epoch_eval_time, i))
			epoch_start_time = time.time()
            # print stats
			print('\nModel saved to disk at iteration #{} with loss:{}'.format(i, val_loss))
			sys.stdout.flush()
		return sess

	def restore_last_session(self):
		saver = tf.train.Saver()
        # create a session
		sess = tf.Session()

        # get checkpoint state
		ckpt = tf.train.get_checkpoint_state(self.checkPointPath)
        # restore session
		if ckpt and ckpt.model_checkpoint_path:
			saver.restore(sess, ckpt.model_checkpoint_path)
			print("Restoring model from: {}".format(ckpt.model_checkpoint_path))
		else:
			print("No checkpoint to restore model from")
        # return to user
		return sess

    # prediction
	def predict(self, sess, X):
		feedDictionary = {self.enc_ip[t]: X[t] for t in range(self.xseq_len)}
		feedDictionary[self.keep_prob] = 1.
		decodeOpEval = sess.run(self.decode_outputs_test_fwd, feedDictionary)
        # dec_op_v is a list; also need to transpose 0,1 indices
        #  (interchange batch_size and timesteps dimensions
		decodeOpEval = np.array(decodeOpEval).transpose([1,0,2])
        # return the index of item with highest probability
		return np.argmax(decodeOpEval, axis=2)

if __name__ == "__main__":
	print("nothing to show here")
	print("Run the main.py")
else:
	print("Module used:",__name__)