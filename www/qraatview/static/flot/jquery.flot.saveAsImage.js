




<!DOCTYPE html>
<html class="   ">
  <head prefix="og: http://ogp.me/ns# fb: http://ogp.me/ns/fb# object: http://ogp.me/ns/object# article: http://ogp.me/ns/article# profile: http://ogp.me/ns/profile#">
    <meta charset='utf-8'>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    
    
    <title>Jeff-Tian/jquery.flot.saveAsImage.js</title>
    <link rel="search" type="application/opensearchdescription+xml" href="/opensearch.xml" title="GitHub" />
    <link rel="fluid-icon" href="https://github.com/fluidicon.png" title="GitHub" />
    <link rel="apple-touch-icon" sizes="57x57" href="/apple-touch-icon-114.png" />
    <link rel="apple-touch-icon" sizes="114x114" href="/apple-touch-icon-114.png" />
    <link rel="apple-touch-icon" sizes="72x72" href="/apple-touch-icon-144.png" />
    <link rel="apple-touch-icon" sizes="144x144" href="/apple-touch-icon-144.png" />
    <meta property="fb:app_id" content="1401488693436528"/>

      <meta content="@github" name="twitter:site" /><meta content="summary" name="twitter:card" /><meta content="Jeff-Tian/jquery.flot.saveAsImage.js" name="twitter:title" /><meta content="jquery.flot.saveAsImage.js - Flot plugin that adds a function to allow user save the current graph as an image by right clicking on the graph and then choose &amp;quot;Save image as ...&amp;quot; to local dis" name="twitter:description" /><meta content="https://avatars0.githubusercontent.com/u/3367820?s=400" name="twitter:image:src" />
<meta content="GitHub" property="og:site_name" /><meta content="object" property="og:type" /><meta content="https://avatars0.githubusercontent.com/u/3367820?s=400" property="og:image" /><meta content="Jeff-Tian/jquery.flot.saveAsImage.js" property="og:title" /><meta content="https://github.com/Jeff-Tian/jquery.flot.saveAsImage.js" property="og:url" /><meta content="jquery.flot.saveAsImage.js - Flot plugin that adds a function to allow user save the current graph as an image by right clicking on the graph and then choose &quot;Save image as ...&quot; to local disk." property="og:description" />

    <link rel="assets" href="https://assets-cdn.github.com/">
    <link rel="conduit-xhr" href="https://ghconduit.com:25035">
    <link rel="xhr-socket" href="/_sockets" />

    <meta name="msapplication-TileImage" content="/windows-tile.png" />
    <meta name="msapplication-TileColor" content="#ffffff" />
    <meta name="selected-link" value="repo_source" data-pjax-transient />
      <meta name="google-analytics" content="UA-3769691-2">

    <meta content="collector.githubapp.com" name="octolytics-host" /><meta content="collector-cdn.github.com" name="octolytics-script-host" /><meta content="github" name="octolytics-app-id" /><meta content="A9EDDC85:3141:26A818:53B44999" name="octolytics-dimension-request_id" /><meta content="7544318" name="octolytics-actor-id" /><meta content="amakmuri" name="octolytics-actor-login" /><meta content="38e0f03ce64a3dc412c7663da50896443f4faa29d1b9915471b17546397bdbaa" name="octolytics-actor-hash" />
    

    
    
    <link rel="icon" type="image/x-icon" href="https://assets-cdn.github.com/favicon.ico" />


    <meta content="authenticity_token" name="csrf-param" />
<meta content="zA1jNEXk09vByMRG3c5eMG0PMWSElKPWP+ejyaesbfeMrmTZ4oWOXKdqhVYk4pk2HdlWJRcc5ZNwGiMl7/zw1A==" name="csrf-token" />

    <link href="https://assets-cdn.github.com/assets/github-a3943029fb2330481c4a6367eccd68e84b5cb8d7.css" media="all" rel="stylesheet" type="text/css" />
    <link href="https://assets-cdn.github.com/assets/github2-bb63b855e5e18db898c33c27a431a6f17937a7cf.css" media="all" rel="stylesheet" type="text/css" />
    


    <meta http-equiv="x-pjax-version" content="85e39934c9c3c6ab5cd2f0e607adff92">

      
  <meta name="description" content="jquery.flot.saveAsImage.js - Flot plugin that adds a function to allow user save the current graph as an image by right clicking on the graph and then choose &quot;Save image as ...&quot; to local disk." />


  <meta content="3367820" name="octolytics-dimension-user_id" /><meta content="Jeff-Tian" name="octolytics-dimension-user_login" /><meta content="11124087" name="octolytics-dimension-repository_id" /><meta content="Jeff-Tian/jquery.flot.saveAsImage.js" name="octolytics-dimension-repository_nwo" /><meta content="true" name="octolytics-dimension-repository_public" /><meta content="false" name="octolytics-dimension-repository_is_fork" /><meta content="11124087" name="octolytics-dimension-repository_network_root_id" /><meta content="Jeff-Tian/jquery.flot.saveAsImage.js" name="octolytics-dimension-repository_network_root_nwo" />

  <link href="https://github.com/Jeff-Tian/jquery.flot.saveAsImage.js/commits/master.atom" rel="alternate" title="Recent Commits to jquery.flot.saveAsImage.js:master" type="application/atom+xml" />

  </head>


  <body class="logged_in  env-production linux vis-public">
    <a href="#start-of-content" tabindex="1" class="accessibility-aid js-skip-to-content">Skip to content</a>
    <div class="wrapper">
      
      
      
      


      <div class="header header-logged-in true">
  <div class="container clearfix">

    <a class="header-logo-invertocat" href="https://github.com/" aria-label="Homepage">
  <span class="mega-octicon octicon-mark-github"></span>
</a>


    
    <a href="/notifications" aria-label="You have no unread notifications" class="notification-indicator tooltipped tooltipped-s" data-hotkey="g n">
        <span class="mail-status all-read"></span>
</a>

      <div class="command-bar js-command-bar  in-repository">
          <form accept-charset="UTF-8" action="/search" class="command-bar-form" id="top_search_form" method="get">

<div class="commandbar">
  <span class="message"></span>
  <input type="text" data-hotkey="s" name="q" id="js-command-bar-field" placeholder="Search or type a command" tabindex="1" autocapitalize="off"
    
    data-username="amakmuri"
      data-repo="Jeff-Tian/jquery.flot.saveAsImage.js"
      data-branch="master"
      data-sha="d8166d24f5d7e26a7884a23976ff94ebdf5bbab0"
  >
  <div class="display hidden"></div>
</div>

    <input type="hidden" name="nwo" value="Jeff-Tian/jquery.flot.saveAsImage.js" />

    <div class="select-menu js-menu-container js-select-menu search-context-select-menu">
      <span class="minibutton select-menu-button js-menu-target" role="button" aria-haspopup="true">
        <span class="js-select-button">This repository</span>
      </span>

      <div class="select-menu-modal-holder js-menu-content js-navigation-container" aria-hidden="true">
        <div class="select-menu-modal">

          <div class="select-menu-item js-navigation-item js-this-repository-navigation-item selected">
            <span class="select-menu-item-icon octicon octicon-check"></span>
            <input type="radio" class="js-search-this-repository" name="search_target" value="repository" checked="checked" />
            <div class="select-menu-item-text js-select-button-text">This repository</div>
          </div> <!-- /.select-menu-item -->

          <div class="select-menu-item js-navigation-item js-all-repositories-navigation-item">
            <span class="select-menu-item-icon octicon octicon-check"></span>
            <input type="radio" name="search_target" value="global" />
            <div class="select-menu-item-text js-select-button-text">All repositories</div>
          </div> <!-- /.select-menu-item -->

        </div>
      </div>
    </div>

  <span class="help tooltipped tooltipped-s" aria-label="Show command bar help">
    <span class="octicon octicon-question"></span>
  </span>


  <input type="hidden" name="ref" value="cmdform">

</form>
        <ul class="top-nav">
          <li class="explore"><a href="/explore">Explore</a></li>
            <li><a href="https://gist.github.com">Gist</a></li>
            <li><a href="/blog">Blog</a></li>
          <li><a href="https://help.github.com">Help</a></li>
        </ul>
      </div>

    


  <ul id="user-links">
    <li>
      <a href="/amakmuri" class="name">
        <img alt="amakmuri" class=" js-avatar" data-user="7544318" height="20" src="https://avatars2.githubusercontent.com/u/7544318?s=140" width="20" /> amakmuri
      </a>
    </li>

    <li class="new-menu dropdown-toggle js-menu-container">
      <a href="#" class="js-menu-target tooltipped tooltipped-s" aria-label="Create new...">
        <span class="octicon octicon-plus"></span>
        <span class="dropdown-arrow"></span>
      </a>

      <div class="new-menu-content js-menu-content">
      </div>
    </li>

    <li>
      <a href="/settings/profile" id="account_settings"
        class="tooltipped tooltipped-s"
        aria-label="Account settings ">
        <span class="octicon octicon-tools"></span>
      </a>
    </li>
    <li>
      <form class="logout-form" action="/logout" method="post">
        <button class="sign-out-button tooltipped tooltipped-s" aria-label="Sign out">
          <span class="octicon octicon-sign-out"></span>
        </button>
      </form>
    </li>

  </ul>

<div class="js-new-dropdown-contents hidden">
  

<ul class="dropdown-menu">
  <li>
    <a href="/new"><span class="octicon octicon-repo"></span> New repository</a>
  </li>
  <li>
    <a href="/organizations/new"><span class="octicon octicon-organization"></span> New organization</a>
  </li>


    <li class="section-title">
      <span title="Jeff-Tian/jquery.flot.saveAsImage.js">This repository</span>
    </li>
      <li>
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/issues/new"><span class="octicon octicon-issue-opened"></span> New issue</a>
      </li>
</ul>

</div>


    
  </div>
</div>

      

        



      <div id="start-of-content" class="accessibility-aid"></div>
          <div class="site" itemscope itemtype="http://schema.org/WebPage">
    <div id="js-flash-container">
      
    </div>
    <div class="pagehead repohead instapaper_ignore readability-menu">
      <div class="container">
        
<ul class="pagehead-actions">

    <li class="subscription">
      <form accept-charset="UTF-8" action="/notifications/subscribe" class="js-social-container" data-autosubmit="true" data-remote="true" method="post"><div style="margin:0;padding:0;display:inline"><input name="authenticity_token" type="hidden" value="68IN8MEVfT2YE3BBh11zAMJdhJCfJYvwNUQQO3majwK8Fbx2xa0vmKi54YfD1iyBr1q4Ju46ZzfFgumnkCqvxg==" /></div>  <input id="repository_id" name="repository_id" type="hidden" value="11124087" />

    <div class="select-menu js-menu-container js-select-menu">
      <a class="social-count js-social-count" href="/Jeff-Tian/jquery.flot.saveAsImage.js/watchers">
        2
      </a>
      <span class="minibutton select-menu-button with-count js-menu-target" role="button" tabindex="0" aria-haspopup="true">
        <span class="js-select-button">
          <span class="octicon octicon-eye"></span>
          Watch
        </span>
      </span>

      <div class="select-menu-modal-holder">
        <div class="select-menu-modal subscription-menu-modal js-menu-content" aria-hidden="true">
          <div class="select-menu-header">
            <span class="select-menu-title">Notification status</span>
            <span class="octicon octicon-x js-menu-close"></span>
          </div> <!-- /.select-menu-header -->

          <div class="select-menu-list js-navigation-container" role="menu">

            <div class="select-menu-item js-navigation-item selected" role="menuitem" tabindex="0">
              <span class="select-menu-item-icon octicon octicon-check"></span>
              <div class="select-menu-item-text">
                <input checked="checked" id="do_included" name="do" type="radio" value="included" />
                <h4>Not watching</h4>
                <span class="description">You only receive notifications for conversations in which you participate or are @mentioned.</span>
                <span class="js-select-button-text hidden-select-button-text">
                  <span class="octicon octicon-eye"></span>
                  Watch
                </span>
              </div>
            </div> <!-- /.select-menu-item -->

            <div class="select-menu-item js-navigation-item " role="menuitem" tabindex="0">
              <span class="select-menu-item-icon octicon octicon octicon-check"></span>
              <div class="select-menu-item-text">
                <input id="do_subscribed" name="do" type="radio" value="subscribed" />
                <h4>Watching</h4>
                <span class="description">You receive notifications for all conversations in this repository.</span>
                <span class="js-select-button-text hidden-select-button-text">
                  <span class="octicon octicon-eye"></span>
                  Unwatch
                </span>
              </div>
            </div> <!-- /.select-menu-item -->

            <div class="select-menu-item js-navigation-item " role="menuitem" tabindex="0">
              <span class="select-menu-item-icon octicon octicon-check"></span>
              <div class="select-menu-item-text">
                <input id="do_ignore" name="do" type="radio" value="ignore" />
                <h4>Ignoring</h4>
                <span class="description">You do not receive any notifications for conversations in this repository.</span>
                <span class="js-select-button-text hidden-select-button-text">
                  <span class="octicon octicon-mute"></span>
                  Stop ignoring
                </span>
              </div>
            </div> <!-- /.select-menu-item -->

          </div> <!-- /.select-menu-list -->

        </div> <!-- /.select-menu-modal -->
      </div> <!-- /.select-menu-modal-holder -->
    </div> <!-- /.select-menu -->

</form>
    </li>

  <li>
    

  <div class="js-toggler-container js-social-container starring-container ">

    <form accept-charset="UTF-8" action="/Jeff-Tian/jquery.flot.saveAsImage.js/unstar" class="js-toggler-form starred" data-remote="true" method="post"><div style="margin:0;padding:0;display:inline"><input name="authenticity_token" type="hidden" value="hWpoQXj+UE0c0oczVLr29ODknKnAOlu91Y0jRZUgaxmfU3IcoFmu9+Q6iGexP37zVWNstxNwONm6PdPoUVvbWg==" /></div>
      <button
        class="minibutton with-count js-toggler-target star-button"
        aria-label="Unstar this repository" title="Unstar Jeff-Tian/jquery.flot.saveAsImage.js">
        <span class="octicon octicon-star"></span>
        Unstar
      </button>
        <a class="social-count js-social-count" href="/Jeff-Tian/jquery.flot.saveAsImage.js/stargazers">
          6
        </a>
</form>
    <form accept-charset="UTF-8" action="/Jeff-Tian/jquery.flot.saveAsImage.js/star" class="js-toggler-form unstarred" data-remote="true" method="post"><div style="margin:0;padding:0;display:inline"><input name="authenticity_token" type="hidden" value="MkNq5zbNt4CB/qLGxGL3z6+mGHrRvcJIZkSZ02mhCZIri2YmdvdI9TqAOY1OC8mW/izh5CyYTygkeXEuwkgL3A==" /></div>
      <button
        class="minibutton with-count js-toggler-target star-button"
        aria-label="Star this repository" title="Star Jeff-Tian/jquery.flot.saveAsImage.js">
        <span class="octicon octicon-star"></span>
        Star
      </button>
        <a class="social-count js-social-count" href="/Jeff-Tian/jquery.flot.saveAsImage.js/stargazers">
          6
        </a>
</form>  </div>

  </li>


        <li>
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/fork" class="minibutton with-count js-toggler-target fork-button lighter tooltipped-n" title="Fork your own copy of Jeff-Tian/jquery.flot.saveAsImage.js to your account" aria-label="Fork your own copy of Jeff-Tian/jquery.flot.saveAsImage.js to your account" rel="facebox nofollow">
            <span class="octicon octicon-repo-forked"></span>
            Fork
          </a>
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/network" class="social-count">5</a>
        </li>

</ul>

        <h1 itemscope itemtype="http://data-vocabulary.org/Breadcrumb" class="entry-title public">
          <span class="repo-label"><span>public</span></span>
          <span class="mega-octicon octicon-repo"></span>
          <span class="author"><a href="/Jeff-Tian" class="url fn" itemprop="url" rel="author"><span itemprop="title">Jeff-Tian</span></a></span><!--
       --><span class="path-divider">/</span><!--
       --><strong><a href="/Jeff-Tian/jquery.flot.saveAsImage.js" class="js-current-repository js-repo-home-link">jquery.flot.saveAsImage.js</a></strong>

          <span class="page-context-loader">
            <img alt="" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
          </span>

        </h1>
      </div><!-- /.container -->
    </div><!-- /.repohead -->

    <div class="container">
      <div class="repository-with-sidebar repo-container new-discussion-timeline js-new-discussion-timeline with-full-navigation ">
        <div class="repository-sidebar clearfix">
            

<div class="sunken-menu vertical-right repo-nav js-repo-nav js-repository-container-pjax js-octicon-loaders">
  <div class="sunken-menu-contents">
    <ul class="sunken-menu-group">
      <li class="tooltipped tooltipped-w" aria-label="Code">
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js" aria-label="Code" class="selected js-selected-navigation-item sunken-menu-item" data-hotkey="g c" data-pjax="true" data-selected-links="repo_source repo_downloads repo_commits repo_releases repo_tags repo_branches /Jeff-Tian/jquery.flot.saveAsImage.js">
          <span class="octicon octicon-code"></span> <span class="full-word">Code</span>
          <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>      </li>

        <li class="tooltipped tooltipped-w" aria-label="Issues">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/issues" aria-label="Issues" class="js-selected-navigation-item sunken-menu-item js-disable-pjax" data-hotkey="g i" data-selected-links="repo_issues /Jeff-Tian/jquery.flot.saveAsImage.js/issues">
            <span class="octicon octicon-issue-opened"></span> <span class="full-word">Issues</span>
            <span class='counter'>0</span>
            <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>        </li>

      <li class="tooltipped tooltipped-w" aria-label="Pull Requests">
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/pulls" aria-label="Pull Requests" class="js-selected-navigation-item sunken-menu-item js-disable-pjax" data-hotkey="g p" data-selected-links="repo_pulls /Jeff-Tian/jquery.flot.saveAsImage.js/pulls">
            <span class="octicon octicon-git-pull-request"></span> <span class="full-word">Pull Requests</span>
            <span class='counter'>0</span>
            <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>      </li>


        <li class="tooltipped tooltipped-w" aria-label="Wiki">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/wiki" aria-label="Wiki" class="js-selected-navigation-item sunken-menu-item js-disable-pjax" data-hotkey="g w" data-selected-links="repo_wiki /Jeff-Tian/jquery.flot.saveAsImage.js/wiki">
            <span class="octicon octicon-book"></span> <span class="full-word">Wiki</span>
            <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>        </li>
    </ul>
    <div class="sunken-menu-separator"></div>
    <ul class="sunken-menu-group">

      <li class="tooltipped tooltipped-w" aria-label="Pulse">
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/pulse" aria-label="Pulse" class="js-selected-navigation-item sunken-menu-item" data-pjax="true" data-selected-links="pulse /Jeff-Tian/jquery.flot.saveAsImage.js/pulse">
          <span class="octicon octicon-pulse"></span> <span class="full-word">Pulse</span>
          <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>      </li>

      <li class="tooltipped tooltipped-w" aria-label="Graphs">
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/graphs" aria-label="Graphs" class="js-selected-navigation-item sunken-menu-item" data-pjax="true" data-selected-links="repo_graphs repo_contributors /Jeff-Tian/jquery.flot.saveAsImage.js/graphs">
          <span class="octicon octicon-graph"></span> <span class="full-word">Graphs</span>
          <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>      </li>

      <li class="tooltipped tooltipped-w" aria-label="Network">
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/network" aria-label="Network" class="js-selected-navigation-item sunken-menu-item js-disable-pjax" data-selected-links="repo_network /Jeff-Tian/jquery.flot.saveAsImage.js/network">
          <span class="octicon octicon-repo-forked"></span> <span class="full-word">Network</span>
          <img alt="" class="mini-loader" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
</a>      </li>
    </ul>


  </div>
</div>

              <div class="only-with-full-nav">
                

  

<div class="clone-url open"
  data-protocol-type="http"
  data-url="/users/set_protocol?protocol_selector=http&amp;protocol_type=clone">
  <h3><strong>HTTPS</strong> clone URL</h3>
  <div class="clone-url-box">
    <input type="text" class="clone js-url-field"
           value="https://github.com/Jeff-Tian/jquery.flot.saveAsImage.js.git" readonly="readonly">
    <span class="url-box-clippy">
    <button aria-label="Copy to clipboard" class="js-zeroclipboard minibutton zeroclipboard-button" data-clipboard-text="https://github.com/Jeff-Tian/jquery.flot.saveAsImage.js.git" data-copied-hint="Copied!" type="button"><span class="octicon octicon-clippy"></span></button>
    </span>
  </div>
</div>

  

<div class="clone-url "
  data-protocol-type="ssh"
  data-url="/users/set_protocol?protocol_selector=ssh&amp;protocol_type=clone">
  <h3><strong>SSH</strong> clone URL</h3>
  <div class="clone-url-box">
    <input type="text" class="clone js-url-field"
           value="git@github.com:Jeff-Tian/jquery.flot.saveAsImage.js.git" readonly="readonly">
    <span class="url-box-clippy">
    <button aria-label="Copy to clipboard" class="js-zeroclipboard minibutton zeroclipboard-button" data-clipboard-text="git@github.com:Jeff-Tian/jquery.flot.saveAsImage.js.git" data-copied-hint="Copied!" type="button"><span class="octicon octicon-clippy"></span></button>
    </span>
  </div>
</div>

  

<div class="clone-url "
  data-protocol-type="subversion"
  data-url="/users/set_protocol?protocol_selector=subversion&amp;protocol_type=clone">
  <h3><strong>Subversion</strong> checkout URL</h3>
  <div class="clone-url-box">
    <input type="text" class="clone js-url-field"
           value="https://github.com/Jeff-Tian/jquery.flot.saveAsImage.js" readonly="readonly">
    <span class="url-box-clippy">
    <button aria-label="Copy to clipboard" class="js-zeroclipboard minibutton zeroclipboard-button" data-clipboard-text="https://github.com/Jeff-Tian/jquery.flot.saveAsImage.js" data-copied-hint="Copied!" type="button"><span class="octicon octicon-clippy"></span></button>
    </span>
  </div>
</div>


<p class="clone-options">You can clone with
      <a href="#" class="js-clone-selector" data-protocol="http">HTTPS</a>,
      <a href="#" class="js-clone-selector" data-protocol="ssh">SSH</a>,
      or <a href="#" class="js-clone-selector" data-protocol="subversion">Subversion</a>.
  <a href="https://help.github.com/articles/which-remote-url-should-i-use" class="help tooltipped tooltipped-n" aria-label="Get help on which URL is right for you.">
    <span class="octicon octicon-question"></span>
  </a>
</p>



                <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/archive/master.zip"
                   class="minibutton sidebar-button"
                   aria-label="Download Jeff-Tian/jquery.flot.saveAsImage.js as a zip file"
                   title="Download Jeff-Tian/jquery.flot.saveAsImage.js as a zip file"
                   rel="nofollow">
                  <span class="octicon octicon-cloud-download"></span>
                  Download ZIP
                </a>
              </div>
        </div><!-- /.repository-sidebar -->

        <div id="js-repo-pjax-container" class="repository-content context-loader-container" data-pjax-container>
          

<span id="js-show-full-navigation"></span>

<div class="repository-meta js-details-container ">
    <div class="repository-description js-details-show">
      <p>Flot plugin that adds a function to allow user save the current graph as an image by right clicking on the graph and then choose "Save image as ..." to local disk.</p>
    </div>

    <div class="repository-website js-details-show">
      <p><a href="http://jeff-tian.github.io/jquery.flot.saveAsImage.js/" rel="nofollow">http://jeff-tian.github.io/jquery.flot.saveAsImage.js/</a></p>
    </div>


</div>

<div class="capped-box overall-summary ">

  <div class="stats-switcher-viewport js-stats-switcher-viewport">
    <div class="stats-switcher-wrapper">
    <ul class="numbers-summary">
      <li class="commits">
        <a data-pjax href="/Jeff-Tian/jquery.flot.saveAsImage.js/commits/master">
            <span class="num">
              <span class="octicon octicon-history"></span>
              10
            </span>
            commits
        </a>
      </li>
      <li>
        <a data-pjax href="/Jeff-Tian/jquery.flot.saveAsImage.js/branches">
          <span class="num">
            <span class="octicon octicon-git-branch"></span>
            2
          </span>
          branches
        </a>
      </li>

      <li>
        <a data-pjax href="/Jeff-Tian/jquery.flot.saveAsImage.js/releases">
          <span class="num">
            <span class="octicon octicon-tag"></span>
            0
          </span>
          releases
        </a>
      </li>

      <li>
        
  <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/graphs/contributors">
    <span class="num">
      <span class="octicon octicon-organization"></span>
      1
    </span>
    contributor
  </a>
      </li>
    </ul>

      <div class="repository-lang-stats">
        <ol class="repository-lang-stats-numbers">
          <li>
              <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/search?l=javascript">
                <span class="color-block language-color" style="background-color:#f1e05a;"></span>
                <span class="lang">JavaScript</span>
                <span class="percent">99.3%</span>
              </a>
          </li>
          <li>
              <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/search?l=css">
                <span class="color-block language-color" style="background-color:#563d7c;"></span>
                <span class="lang">CSS</span>
                <span class="percent">0.7%</span>
              </a>
          </li>
        </ol>
      </div>
    </div>
  </div>

</div>

  <div class="tooltipped tooltipped-s" aria-label="Show language statistics">
    <a href="#"
     class="repository-lang-stats-graph js-toggle-lang-stats"
     style="background-color:#563d7c">
  <span class="language-color" style="width:99.3%; background-color:#f1e05a;" itemprop="keywords">JavaScript</span><span class="language-color" style="width:0.7%; background-color:#563d7c;" itemprop="keywords">CSS</span>
    </a>
  </div>




<div class="file-navigation in-mid-page">
  <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/find/master"
        class="js-show-file-finder minibutton empty-icon tooltipped tooltipped-s right"
        data-pjax
        data-hotkey="t"
        aria-label="Quickly jump between files">
    <span class="octicon octicon-list-unordered"></span>
  </a>
    <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/compare" aria-label="Compare, review, create a pull request" class="minibutton compact primary tooltipped tooltipped-s" aria-label="Compare &amp; review" data-pjax>
      <span class="octicon octicon-git-compare"></span>
    </a>

  

<div class="select-menu js-menu-container js-select-menu" >
  <span class="minibutton select-menu-button js-menu-target css-truncate" data-hotkey="w"
    data-master-branch="master"
    data-ref="master"
    title="master"
    role="button" aria-label="Switch branches or tags" tabindex="0" aria-haspopup="true">
    <span class="octicon octicon-git-branch"></span>
    <i>branch:</i>
    <span class="js-select-button css-truncate-target">master</span>
  </span>

  <div class="select-menu-modal-holder js-menu-content js-navigation-container" data-pjax aria-hidden="true">

    <div class="select-menu-modal">
      <div class="select-menu-header">
        <span class="select-menu-title">Switch branches/tags</span>
        <span class="octicon octicon-x js-menu-close"></span>
      </div> <!-- /.select-menu-header -->

      <div class="select-menu-filters">
        <div class="select-menu-text-filter">
          <input type="text" aria-label="Filter branches/tags" id="context-commitish-filter-field" class="js-filterable-field js-navigation-enable" placeholder="Filter branches/tags">
        </div>
        <div class="select-menu-tabs">
          <ul>
            <li class="select-menu-tab">
              <a href="#" data-tab-filter="branches" class="js-select-menu-tab">Branches</a>
            </li>
            <li class="select-menu-tab">
              <a href="#" data-tab-filter="tags" class="js-select-menu-tab">Tags</a>
            </li>
          </ul>
        </div><!-- /.select-menu-tabs -->
      </div><!-- /.select-menu-filters -->

      <div class="select-menu-list select-menu-tab-bucket js-select-menu-tab-bucket" data-tab-filter="branches">

        <div data-filterable-for="context-commitish-filter-field" data-filterable-type="substring">


            <div class="select-menu-item js-navigation-item ">
              <span class="select-menu-item-icon octicon octicon-check"></span>
              <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/tree/gh-pages"
                 data-name="gh-pages"
                 data-skip-pjax="true"
                 rel="nofollow"
                 class="js-navigation-open select-menu-item-text css-truncate-target"
                 title="gh-pages">gh-pages</a>
            </div> <!-- /.select-menu-item -->
            <div class="select-menu-item js-navigation-item selected">
              <span class="select-menu-item-icon octicon octicon-check"></span>
              <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/tree/master"
                 data-name="master"
                 data-skip-pjax="true"
                 rel="nofollow"
                 class="js-navigation-open select-menu-item-text css-truncate-target"
                 title="master">master</a>
            </div> <!-- /.select-menu-item -->
        </div>

          <div class="select-menu-no-results">Nothing to show</div>
      </div> <!-- /.select-menu-list -->

      <div class="select-menu-list select-menu-tab-bucket js-select-menu-tab-bucket" data-tab-filter="tags">
        <div data-filterable-for="context-commitish-filter-field" data-filterable-type="substring">


        </div>

        <div class="select-menu-no-results">Nothing to show</div>
      </div> <!-- /.select-menu-list -->

    </div> <!-- /.select-menu-modal -->
  </div> <!-- /.select-menu-modal-holder -->
</div> <!-- /.select-menu -->



  <div class="breadcrumb"><span class='repo-root js-repo-root'><span itemscope="" itemtype="http://data-vocabulary.org/Breadcrumb"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js" data-branch="master" data-direction="back" data-pjax="true" itemscope="url"><span itemprop="title">jquery.flot.saveAsImage.js</span></a></span></span><span class="separator"> / </span><form action="/Jeff-Tian/jquery.flot.saveAsImage.js/new/master" aria-label="Fork this project and create a new file" class="js-new-blob-form tooltipped tooltipped-e new-file-link" method="post"><span aria-label="Fork this project and create a new file" class="js-new-blob-submit octicon octicon-plus" data-test-id="create-new-git-file" role="button"></span></form></div>
</div>




  
  <div class="commit commit-tease js-details-container" >
    <p class="commit-title ">
        <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/481ba36b8b6ab26dea8dfbdfc6690d7c59ea4dba" class="message" data-pjax="true" title="Use [class] instead of .class to avoid errors in IE 8.">Use [class] instead of .class to avoid errors in IE 8.</a>
        
    </p>
    <div class="commit-meta">
      <button aria-label="Copy SHA" class="js-zeroclipboard zeroclipboard-link" data-clipboard-text="481ba36b8b6ab26dea8dfbdfc6690d7c59ea4dba" data-copied-hint="copied!" type="button"><span class="octicon octicon-clippy"></span></button>
      <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/481ba36b8b6ab26dea8dfbdfc6690d7c59ea4dba" class="sha-block" data-pjax>latest commit <span class="sha">481ba36b8b</span></a>

      <div class="authorship">
        <img alt="Jeff" class="gravatar js-avatar" data-user="3367820" height="20" src="https://avatars3.githubusercontent.com/u/3367820?s=140" width="20" />
        <span class="author-name"><a href="/Jeff-Tian" data-skip-pjax="true" rel="author">Jeff-Tian</a></span>
        authored <time class="updated" datetime="2014-05-29T19:45:19+08:00" is="relative-time">May 29, 2014</time>

      </div>
    </div>
  </div>

  <div class="file-wrap">
    <table class="files" data-pjax>

      
<tbody class=""
  data-url="/Jeff-Tian/jquery.flot.saveAsImage.js/file-list/master"
  data-deferred-content-error="Failed to load latest commit information.">

    <tr>
      <td class="icon">
        <span class="octicon octicon-file-directory"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/tree/master/examples" class="js-directory-link" id="bfebe34154a0dfd9fc7b447fc9ed74e9-30a0933e410268d63f1196f4b40f03130d2d24af" title="examples">examples</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/d1f66d66d418c980891ab16f3f1d9caa93482d55" class="message" data-pjax="true" title="Fix a bug for jquery.flot.saveAsImage.js on Ubuntu Chrome; Update example page.">Fix a bug for jquery.flot.saveAsImage.js on Ubuntu Chrome; Update exa…</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2013-11-21T13:55:44Z" is="time-ago">November 21, 2013</time></span>
      </td>
    </tr>
    <tr>
      <td class="icon">
        <span class="octicon octicon-file-directory"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/tree/master/lib" class="js-directory-link" id="e8acc63b1e238f3255c900eed37254b8-8e5981e24098073b5c9dc3d14ab5ec752cae0c46" title="lib">lib</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/1a5b5b6415b421891115464bb08e6381e9cede9e" class="message" data-pjax="true" title="Better structure. Add detail example page.">Better structure. Add detail example page.</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2013-11-07T07:30:45Z" is="time-ago">November 07, 2013</time></span>
      </td>
    </tr>
    <tr>
      <td class="icon">
        <span class="octicon octicon-file-text"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/blob/master/.gitattributes" class="js-directory-link" id="fc723d30b02a4cca7a534518111c1a66-412eeda78dc9de1186c2e0e1526764af82ab3431" title=".gitattributes">.gitattributes</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/44682b7cd9ec7599b4cb9a42c3d508c1de0a821d" class="message" data-pjax="true" title="Initial check in.">Initial check in.</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2013-07-02T12:09:39Z" is="time-ago">July 02, 2013</time></span>
      </td>
    </tr>
    <tr>
      <td class="icon">
        <span class="octicon octicon-file-text"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/blob/master/.gitignore" class="js-directory-link" id="a084b794bc0759e7a6b77810e01874f2-b9d6bd92f5f09e195d6bc19536500b6494dd2b75" title=".gitignore">.gitignore</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/44682b7cd9ec7599b4cb9a42c3d508c1de0a821d" class="message" data-pjax="true" title="Initial check in.">Initial check in.</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2013-07-02T12:09:39Z" is="time-ago">July 02, 2013</time></span>
      </td>
    </tr>
    <tr>
      <td class="icon">
        <span class="octicon octicon-file-text"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/blob/master/README.md" class="js-directory-link" id="04c6e90faac2675aa89e2176d2eec7d8-7248f4380da5d0b92e163cc53b35f88292ec8d36" title="README.md">README.md</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/045242d635329e4bc1f617feb81ed31c2d11880a" class="message" data-pjax="true" title="Update README for saveAsImage.">Update README for saveAsImage.</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2014-05-17T07:24:14Z" is="time-ago">May 17, 2014</time></span>
      </td>
    </tr>
    <tr>
      <td class="icon">
        <span class="octicon octicon-file-text"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/blob/master/canvasAsImage.js" class="js-directory-link" id="02999b36749bebad25bc8452cfdbaa87-7fca9f3b30bc830cc56c13364acf2f447ee387c0" title="canvasAsImage.js">canvasAsImage.js</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/481ba36b8b6ab26dea8dfbdfc6690d7c59ea4dba" class="message" data-pjax="true" title="Use [class] instead of .class to avoid errors in IE 8.">Use [class] instead of .class to avoid errors in IE 8.</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2014-05-29T11:45:19Z" is="time-ago">May 29, 2014</time></span>
      </td>
    </tr>
    <tr>
      <td class="icon">
        <span class="octicon octicon-file-text"></span>
        <img alt="" class="spinner" height="16" src="https://assets-cdn.github.com/images/spinners/octocat-spinner-32.gif" width="16" />
      </td>
      <td class="content">
        <span class="css-truncate css-truncate-target"><a href="/Jeff-Tian/jquery.flot.saveAsImage.js/blob/master/jquery.flot.saveAsImage.js" class="js-directory-link" id="c45de451ee643e8bd6fc823d3b799790-ae80a756d7a0a350e3ebd9723ee74f2095edfa2e" title="jquery.flot.saveAsImage.js">jquery.flot.saveAsImage.js</a></span>
      </td>
      <td class="message">
        <span class="css-truncate css-truncate-target ">
          <a href="/Jeff-Tian/jquery.flot.saveAsImage.js/commit/6f540b4b562aa9e1cf5e8661f544d0fbde4214dd" class="message" data-pjax="true" title="Delete CanvasAsImage object from flot plugin.">Delete CanvasAsImage object from flot plugin.</a>
        </span>
      </td>
      <td class="age">
        <span class="css-truncate css-truncate-target"><time datetime="2014-05-17T09:39:22Z" is="time-ago">May 17, 2014</time></span>
      </td>
    </tr>
</tbody>

    </table>
  </div>


  <div id="readme" class="clearfix announce instapaper_body md">
    <span class="name">
      <span class="octicon octicon-book"></span>
      README.md
    </span>

    <article class="markdown-body entry-content" itemprop="mainContentOfPage"><h1>
<a name="user-content-canvasasimagejs" class="anchor" href="#canvasasimagejs" aria-hidden="true"><span class="octicon octicon-link"></span></a>canvasAsImage.js</h1>

<p>Reference this file in your header of which page you are using canvas, then when you right click on your canvas, a context menu would appeared and gave you a option to save your drawings on canvas as image to your local disk.</p>

<h2>
<a name="user-content-online-examples" class="anchor" href="#online-examples" aria-hidden="true"><span class="octicon octicon-link"></span></a>Online examples:</h2>

<p><a href="http://zizhujy.com/GraphWorld">http://zizhujy.com/GraphWorld</a></p>

<h1>
<a name="user-content-jqueryflotsaveasimagejs" class="anchor" href="#jqueryflotsaveasimagejs" aria-hidden="true"><span class="octicon octicon-link"></span></a>jquery.flot.saveAsImage.js</h1>

<p>Flot plugin that adds a function to allow user save the current graph as an image by right clicking on the graph and then choose "Save image as ..." to local disk.</p>

<p>Copyright (c) 2013 <a href="http://zizhujy.com">http://zizhujy.com</a>.
Licensed under the MIT license.</p>

<h2>
<a name="user-content-screen-shot" class="anchor" href="#screen-shot" aria-hidden="true"><span class="octicon octicon-link"></span></a>Screen shot:</h2>

<p><a href="http://zizhujy.com/blog/post/2013/07/02/A-Flot-plugin-for-saving-canvas-image-to-local-disk.aspx">http://zizhujy.com/blog/post/2013/07/02/A-Flot-plugin-for-saving-canvas-image-to-local-disk.aspx</a></p>

<h2>
<a name="user-content-usage" class="anchor" href="#usage" aria-hidden="true"><span class="octicon octicon-link"></span></a>Usage:</h2>

<p>Inside the </p> area of your html page, add the following lines:

<div class="highlight highlight-html"><pre><span class="nt">&lt;script </span><span class="na">type=</span><span class="s">"text/javascript"</span> <span class="na">src=</span><span class="s">"http://zizhujy.com/Scripts/base64.js"</span><span class="nt">&gt;&lt;/script&gt;</span>
<span class="nt">&lt;script </span><span class="na">type=</span><span class="s">"text/javascript"</span> <span class="na">src=</span><span class="s">"http://zizhujy.com/Scripts/drawing/canvas2image.js"</span><span class="nt">&gt;&lt;/script&gt;</span>
<span class="nt">&lt;script </span><span class="na">type=</span><span class="s">"text/javascript"</span> <span class="na">src=</span><span class="s">"http://zizhujy.com/Scripts/flot/jquery.flot.saveAsImage.js"</span><span class="nt">&gt;&lt;/script&gt;</span>
</pre></div>

<p>Now you are all set. Right click on your flot canvas, you will see the "Save image as ..." option.</p>

<h2>
<a name="user-content-online-examples-1" class="anchor" href="#online-examples-1" aria-hidden="true"><span class="octicon octicon-link"></span></a>Online examples:</h2>

<p><a href="http://zizhujy.com/FunctionGrapher">http://zizhujy.com/FunctionGrapher</a> is using it, you can try right clicking on the function graphs and
you will see you can save the image to local disk.</p>

<h2>
<a name="user-content-dependencies" class="anchor" href="#dependencies" aria-hidden="true"><span class="octicon octicon-link"></span></a>Dependencies:</h2>

<p>This plugin references the base64.js and canvas2image.js.</p>

<h2>
<a name="user-content-customizations" class="anchor" href="#customizations" aria-hidden="true"><span class="octicon octicon-link"></span></a>Customizations:</h2>

<p>The default behavior of this plugin is dynamically creating an image from the flot canvas, and then puts the 
image above the flot canvas. If you want to add some css effects on to the dynamically created image, you can
apply whatever css styles on to it, only remember to make sure the css class name is set correspondingly by 
the options object of this plugin. You can also customize the image format through this options object:</p>

<div class="highlight highlight-javascript"><pre><span class="nx">options</span><span class="o">:</span> <span class="p">{</span>
    <span class="nx">imageClassName</span><span class="o">:</span> <span class="s2">"canvas-image"</span><span class="p">,</span>
    <span class="nx">imageFormat</span><span class="o">:</span> <span class="s2">"png"</span>
<span class="p">}</span>
</pre></div></article>
  </div>


        </div>

      </div><!-- /.repo-container -->
      <div class="modal-backdrop"></div>
    </div><!-- /.container -->
  </div><!-- /.site -->


    </div><!-- /.wrapper -->

      <div class="container">
  <div class="site-footer">
    <ul class="site-footer-links right">
      <li><a href="https://status.github.com/">Status</a></li>
      <li><a href="http://developer.github.com">API</a></li>
      <li><a href="http://training.github.com">Training</a></li>
      <li><a href="http://shop.github.com">Shop</a></li>
      <li><a href="/blog">Blog</a></li>
      <li><a href="/about">About</a></li>

    </ul>

    <a href="/">
      <span class="mega-octicon octicon-mark-github" title="GitHub"></span>
    </a>

    <ul class="site-footer-links">
      <li>&copy; 2014 <span title="0.05966s from github-fe128-cp1-prd.iad.github.net">GitHub</span>, Inc.</li>
        <li><a href="/site/terms">Terms</a></li>
        <li><a href="/site/privacy">Privacy</a></li>
        <li><a href="/security">Security</a></li>
        <li><a href="/contact">Contact</a></li>
    </ul>
  </div><!-- /.site-footer -->
</div><!-- /.container -->


    <div class="fullscreen-overlay js-fullscreen-overlay" id="fullscreen_overlay">
  <div class="fullscreen-container js-fullscreen-container">
    <div class="textarea-wrap">
      <textarea name="fullscreen-contents" id="fullscreen-contents" class="fullscreen-contents js-fullscreen-contents" placeholder="" data-suggester="fullscreen_suggester"></textarea>
    </div>
  </div>
  <div class="fullscreen-sidebar">
    <a href="#" class="exit-fullscreen js-exit-fullscreen tooltipped tooltipped-w" aria-label="Exit Zen Mode">
      <span class="mega-octicon octicon-screen-normal"></span>
    </a>
    <a href="#" class="theme-switcher js-theme-switcher tooltipped tooltipped-w"
      aria-label="Switch themes">
      <span class="octicon octicon-color-mode"></span>
    </a>
  </div>
</div>



    <div id="ajax-error-message" class="flash flash-error">
      <span class="octicon octicon-alert"></span>
      <a href="#" class="octicon octicon-x close js-ajax-error-dismiss" aria-label="Dismiss error"></a>
      Something went wrong with that request. Please try again.
    </div>


      <script crossorigin="anonymous" src="https://assets-cdn.github.com/assets/frameworks-df9e4beac80276ed3dfa56be0d97b536d0f5ee12.js" type="text/javascript"></script>
      <script async="async" crossorigin="anonymous" src="https://assets-cdn.github.com/assets/github-040fe8b89a4441eaff9e4636fa2bbe9ca34fd0d2.js" type="text/javascript"></script>
      
      
        <script async src="https://www.google-analytics.com/analytics.js"></script>
  </body>
</html>

