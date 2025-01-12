
import time
import logging
import tensorflow as tf

logger = logging.getLogger('__main__')

# TODO: add multiprocessing to sampling. Is it necessary or other steps?


class BatchPolicyBase(object):
    """
    Base object for batch optimization policy algorithms.
        Key ingredients:
            policy -- approximator which represents policy to optimize
            baseline -- value to use in calculation of advantage function
            sampler -- collector of data from environment
        Other attributes:
            batch_size -- how many timesteps to collect for 1 iteration of policy
            gamma -- discounting factor
            sess -- tf session

    Child classes should implement methods _init_variables and _optimize_policy.
    """

    def __init__(self,
                 sess,
                 gamma,
                 batch_size,
                 policy,
                 baseline,
                 sampler,
                 monitor_path='experiments'):
        self.sess = sess
        self.gamma = gamma
        self.batch_size = batch_size
        self.policy = policy
        self.baseline = baseline
        self.sampler = sampler
        self.global_step = tf.Variable(0, name='global_step', trainable=False)
        self._init_variables()
        self.summary_op = tf.summary.merge_all()
        self.train_writer = tf.summary.FileWriter(monitor_path + '/train', sess.graph)
        self.test_writer = tf.summary.FileWriter(monitor_path + '/test', sess.graph)
        self.sess.run(tf.global_variables_initializer())
        logger.info('Agent variables initialized.')
        logger.info('Logging directory: {}'.format(monitor_path))

    def collect_samples(self):
        return self.sampler.collect_samples()

    def process_samples(self, samples):
        return self.sampler.process_samples(samples)

    def train_agent(self, n_iter, eval_freq, saver=None, checkpoint_path=None):
        logger.info('Started training.')
        for i in xrange(n_iter):
            logger.info('\n\n' + '*'*40 + '\n' + 'Iteration {} \n'.format(i))

            start_time = time.time()
            samples = self.sampler.collect_samples(self.gamma, self.batch_size)
            logger.info('Collected samples, took {:.2f} sec'.format(time.time() - start_time))

            start_time = time.time()
            self.baseline.fit(samples)
            samples = self.baseline.predict_value(samples)
            logger.info('Fitted baseline, took {:.2f} sec'.format(time.time() - start_time))

            start_time = time.time()
            self._optimize_policy(samples)
            logger.info('Optimized policy, took {:.2f} sec'.format(time.time() - start_time))

            if saver is not None:
                saver.save(self.sess, checkpoint_path)

            if n_iter % eval_freq == 0:
                total_reward, episode_length = self.test_agent(sample=False)
                logger.info('Evaluation. Reward: {:.1f}; Episode length: {}.'.format(total_reward, episode_length))

    def test_agent(self, sample):
        total_reward, episode_length = self.sampler.test_agent(sample, self.sess)

        test_summary = tf.Summary()
        test_summary.value.add(simple_value=total_reward, tag='total_reward')
        t = self.sess.run(self.global_step)
        self.test_writer.add_summary(test_summary, t)

        return total_reward, episode_length

    def _init_variables(self):
        """
        Initialize variables and build computational graph.
        """
        raise NotImplementedError

    def _optimize_policy(self, samples):
        """
        Optimize policy on the basis of data collected.
        """
        raise NotImplementedError



